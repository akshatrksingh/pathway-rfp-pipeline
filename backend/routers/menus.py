from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from schemas import ParsedMenu
from services.menu_parser import parse_menu

router = APIRouter(prefix="/api/menus", tags=["menus"])


@router.post("/parse", response_model=ParsedMenu)
def parse_menu_endpoint(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
):
    """
    Parse a restaurant menu into structured dishes and ingredients.

    Accepts either:
      - multipart file upload (PDF)  →  field name: file
      - form field url               →  field name: url
    """
    if file is None and not url:
        raise HTTPException(status_code=400, detail="Provide either a PDF file or a url.")
    if file is not None and url:
        raise HTTPException(status_code=400, detail="Provide only one of file or url, not both.")

    try:
        if file is not None:
            pdf_bytes = file.file.read()
            result = parse_menu(pdf_bytes=pdf_bytes)
        else:
            result = parse_menu(url=url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")

    return result
