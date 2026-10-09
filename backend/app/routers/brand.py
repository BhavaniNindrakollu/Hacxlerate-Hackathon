"""Brand profile management and setup wizard endpoints."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Brand, OfficialAsset, User
from app.schemas import BrandIn, BrandOut, OfficialAppOut, OfficialSocialOut
from app.security import ANALYST_PLUS, get_current_user, require_roles, write_audit

router = APIRouter(prefix="/brand", tags=["brand"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _to_brand_out(brand: Brand) -> BrandOut:
    keywords = [k.strip() for k in (brand.keywords or "").split(",") if k.strip()]
    socials: list[OfficialSocialOut] = []
    apps: list[OfficialAppOut] = []

    for asset in brand.assets:
        if asset.asset_type == "social":
            socials.append(
                OfficialSocialOut(
                    id=asset.id,
                    platform=asset.platform,
                    handle=asset.handle or "",
                )
            )
        elif asset.asset_type == "app":
            apps.append(
                OfficialAppOut(
                    id=asset.id,
                    store=asset.platform,
                    package_id=asset.package_id or "",
                    developer_name=asset.developer_name or "",
                )
            )

    return BrandOut(
        id=brand.id,
        company_name=brand.company_name,
        logo_url=brand.logo_path,
        keywords=keywords,
        social_accounts=socials,
        official_apps=apps,
        is_demo=bool(brand.is_demo),
    )


@router.get("", response_model=BrandOut | None)
def get_brand(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrandOut | None:
    """Return the shared workspace brand profile."""
    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    if not brand:
        return None
    return _to_brand_out(brand)


def apply_brand_payload(db: Session, payload: BrandIn, *, is_demo: bool) -> Brand:
    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    keywords_str = ",".join(payload.keywords)

    if not brand:
        brand = Brand(
            company_name=payload.company_name,
            keywords=keywords_str,
            is_demo=is_demo,
        )
        db.add(brand)
        db.flush()
    else:
        brand.company_name = payload.company_name
        brand.keywords = keywords_str
        brand.is_demo = is_demo
        for asset in list(brand.assets):
            db.delete(asset)
        db.flush()

    for s in payload.social_accounts:
        db.add(
            OfficialAsset(
                brand_id=brand.id,
                asset_type="social",
                platform=s.platform,
                handle=s.handle,
            )
        )

    for a in payload.official_apps:
        db.add(
            OfficialAsset(
                brand_id=brand.id,
                asset_type="app",
                platform=a.store,
                package_id=a.package_id,
                developer_name=a.developer_name,
            )
        )
    return brand


@router.post("", response_model=BrandOut)
def save_brand(
    payload: BrandIn,
    request: Request,
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> BrandOut:
    """Create or update the shared workspace brand profile. Does not delete detections."""
    brand = apply_brand_payload(db, payload, is_demo=False)
    db.commit()
    db.refresh(brand)
    write_audit(db, user, "save_brand", brand.company_name, request)
    return _to_brand_out(brand)


@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile,
    request: Request,
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Upload official brand logo with validation."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Must be PNG, JPEG, WEBP or SVG.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 5MB.",
        )

    ext = Path(file.filename or "logo.png").suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported logo extension.")
    upload_dir = get_settings().upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"brand_logo_{os.urandom(4).hex()}{ext}"
    dest_path = upload_dir / filename

    with open(dest_path, "wb") as f:
        f.write(contents)

    logo_url = f"/uploads/{filename}"

    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    if brand:
        brand.logo_path = logo_url
        db.commit()

    write_audit(db, user, "upload_logo", filename, request)
    return {"logo_url": logo_url, "filename": filename}


def demo_payload() -> BrandIn:
    return BrandIn(
        company_name="Paytm",
        keywords=["wallet", "payments", "upi", "soundbox", "recharge", "fastag", "bank", "cashback"],
        social_accounts=[
            {"platform": "twitter", "handle": "paytm"},
            {"platform": "instagram", "handle": "paytm"},
            {"platform": "youtube", "handle": "paytm"},
            {"platform": "linkedin", "handle": "paytm"},
            {"platform": "telegram", "handle": "paytmofficial"},
        ],
        official_apps=[
            {
                "store": "play",
                "package_id": "net.one97.paytm",
                "developer_name": "One97 Communications Ltd.",
            },
            {
                "store": "play",
                "package_id": "com.paytm.business",
                "developer_name": "One97 Communications Ltd.",
            },
            {
                "store": "appstore",
                "package_id": "id473941634",
                "developer_name": "One97 Communications",
            },
        ],
    )


def seed_demo_brand(db: Session) -> BrandOut:
    """Internal helper used by first-launch seed. Does not delete detections."""
    brand = apply_brand_payload(db, demo_payload(), is_demo=True)
    brand.logo_path = "/uploads/paytm_official.png"
    db.commit()
    db.refresh(brand)
    return _to_brand_out(brand)


@router.post("/demo", response_model=BrandOut)
def load_demo_brand(
    request: Request,
    confirm_overwrite: bool = Query(False),
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> BrandOut:
    """Load the Paytm demo brand. Never deletes detections, users, or uploaded sample logos."""
    existing = db.scalar(select(Brand).order_by(Brand.id.desc()))
    if existing and not existing.is_demo and not confirm_overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A custom brand profile already exists. Loading the demo would replace the brand "
                "name and official allowlist, but would not delete detection history. "
                "Retry with confirm_overwrite=true if you intend to replace the brand profile."
            ),
        )

    result = seed_demo_brand(db)
    write_audit(db, user, "load_demo_brand", "Paytm", request)
    return result
