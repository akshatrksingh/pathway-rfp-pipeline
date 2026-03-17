from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from schemas import ParsedMenu
from services.menu_parser import parse_menu

router = APIRouter(prefix="/api/menus", tags=["menus"])

_ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "image/webp"}
_ALLOWED_EXT  = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
_MAX_BYTES     = 30 * 1024 * 1024  # 30 MB


def _resolve_content_type(file: UploadFile) -> str:
    """Return normalised MIME type or raise 415."""
    ct  = (file.content_type or "").lower().split(";")[0].strip()
    ext = Path(file.filename or "").suffix.lower()

    # browsers sometimes send image/jpg instead of image/jpeg
    if ct == "image/jpg":
        ct = "image/jpeg"

    if ct in _ALLOWED_MIME:
        return ct

    # fall back to extension if MIME is missing / generic
    _ext_map = {".pdf": "application/pdf", ".png": "image/png",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    if ext in _ext_map:
        return _ext_map[ext]

    raise HTTPException(
        status_code=415,
        detail="Please upload a PDF or image file (PNG, JPG, JPEG).",
    )


@router.post("/parse", response_model=ParsedMenu)
def parse_menu_endpoint(file: UploadFile = File(...)):
    """Parse a restaurant menu from a PDF or image file."""
    content_type = _resolve_content_type(file)
    file_bytes   = file.file.read()

    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File too large. Please upload a file under 10 MB.",
        )

    try:
        result = parse_menu(file_bytes=file_bytes, content_type=content_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="We had trouble reading this file. Please try a different file.",
        )

    return result
