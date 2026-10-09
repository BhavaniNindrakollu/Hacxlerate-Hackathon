"""ImpostorRadar FastAPI Application — Production Single-Service Backend & Static Host."""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import bootstrap_initial_admin, get_session_factory, init_db
from app.models import Brand, User
from app.routers import (
    apps,
    audit,
    auth,
    brand,
    dashboard,
    detections,
    health,
    lookalike,
    social,
    sources,
    takedown,
    users,
)
from app.security import get_current_user

settings = get_settings()


def ensure_seed_uploads(upload_dir: Path) -> None:
    """Copy bundled demo images into the configured upload dir so a fresh host serves them."""
    import shutil

    seed_dir = Path(__file__).resolve().parent / "data" / "seed_uploads"
    for seed_file in seed_dir.glob("*.png"):
        dest = upload_dir / seed_file.name
        if not dest.exists():
            shutil.copyfile(seed_file, dest)


def auto_seed_if_empty() -> None:
    """Pre-seed Paytm demo brand and initial scans on first launch only when the brand table is empty."""
    if settings.environment.lower() == "test":
        return
    db = get_session_factory()()
    try:
        existing_brand = db.query(Brand).first()
        if not existing_brand:
            print("[ImpostorRadar] Pre-seeding demo brand 'Paytm' and running initial scans...")
            from app.routers.apps import run_apps_scan_internal
            from app.routers.brand import seed_demo_brand
            from app.routers.social import run_social_scan_internal

            seed_demo_brand(db)
            run_social_scan_internal(db)
            run_apps_scan_internal(db)
            print("[ImpostorRadar] Pre-seeding complete. Existing later records are never overwritten on restart.")
    except Exception as exc:
        print(f"[ImpostorRadar] Auto-seed error (non-fatal): {exc}")
    finally:
        db.close()


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_settings().upload_path.mkdir(parents=True, exist_ok=True)
    get_settings().backup_path.mkdir(parents=True, exist_ok=True)
    ensure_seed_uploads(get_settings().upload_path)
    bootstrap_initial_admin()
    auto_seed_if_empty()
    yield


app = FastAPI(
    title=settings.app_name,
    description="ImpostorRadar — Digital Risk Protection platform focused on Social & App Monitoring",
    version="1.1.0",
    lifespan=lifespan,
)

cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(brand.router, prefix="/api")
app.include_router(social.router, prefix="/api")
app.include_router(apps.router, prefix="/api")
app.include_router(detections.router, prefix="/api")
app.include_router(lookalike.router, prefix="/api")
app.include_router(takedown.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(sources.router, prefix="/api")


@app.get("/uploads/{filename}")
def serve_upload(filename: str, user: User = Depends(get_current_user)) -> FileResponse:
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid file name.")
    path = get_settings().upload_path / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    # sandbox CSP neutralizes scripts in user-uploaded SVG/HTML opened directly;
    # <img> embedding is governed by this page's headers and still works.
    return FileResponse(
        path,
        headers={
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )


dist_candidates = [
    Path("frontend/dist"),
    Path("../frontend/dist"),
    get_settings().frontend_dist,
    Path("dist"),
]
frontend_dist = next((p for p in dist_candidates if p.exists() and (p / "index.html").exists()), None)

if frontend_dist:
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
