"""
Menu parser service.

Accepts:
  - PDF bytes → pdfplumber text extraction (text-based PDFs)
              → vision fallback if no text found (image/scanned PDFs)
  - URL string → httpx fetch → HTML stripped to text

Then sends extracted text (or image) to LLM and returns a ParsedMenu.
"""

import io
import re
import httpx
import pdfplumber

from schemas import ParsedMenu
from services.llm_client import LLMClient

_SYSTEM_PROMPT = """\
You are a restaurant menu parser. Given raw menu text, extract every dish with its per-serving ingredient quantities and an estimated number of servings sold per day at a mid-size restaurant (~150 covers/day).

Return ONLY a JSON object matching this exact schema — no markdown, no explanation:

{
  "dishes": [
    {
      "name": "string",
      "description": "string or null",
      "category": "string or null  (e.g. Appetizer, Main, Dessert)",
      "servings_per_day": integer,
      "ingredients": [
        {
          "name": "string  (canonical ingredient name, lowercase)",
          "quantity_per_serving": number or null,
          "unit": "string or null  (e.g. kg, lbs, liters, units)",
          "notes": "string or null  (e.g. 'fresh', 'organic')"
        }
      ]
    }
  ]
}

Rules:
- Ingredient names must be canonical and lowercase (e.g. 'mozzarella', not 'Fresh Mozzarella di Bufala').
- quantity_per_serving is the ingredient amount used in ONE serving of that dish (not monthly, not total).
- servings_per_day is your estimate of how many times this dish is ordered per day at a busy mid-size restaurant.
- If the menu text is ambiguous, make reasonable estimates — do not omit dishes.
- Do not include non-food items (cutlery, décor, etc.).
"""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def render_pdf_pages_as_images(pdf_bytes: bytes, max_pages: int = 4, resolution: int = 150) -> list[bytes]:
    """Render each PDF page to a PNG image. Used for image-based/scanned PDFs."""
    images = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:max_pages]:
            img = page.to_image(resolution=resolution).original
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images.append(buf.getvalue())
    return images


def extract_text_from_url(url: str) -> str:
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    html = response.text
    # Strip tags and collapse whitespace
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_menu(*, pdf_bytes: bytes | None = None, url: str | None = None) -> ParsedMenu:
    """
    Extract menu text from either a PDF or a URL, then parse via LLM.
    Exactly one of pdf_bytes or url must be provided.

    For image-based PDFs (scanned, no selectable text), falls back to
    rendering pages as images and sending them to the LLM vision API.
    """
    if pdf_bytes is None and url is None:
        raise ValueError("Provide either pdf_bytes or url.")
    if pdf_bytes is not None and url is not None:
        raise ValueError("Provide only one of pdf_bytes or url, not both.")

    client = LLMClient()

    # --- PDF path ---
    if pdf_bytes is not None:
        raw_text = extract_text_from_pdf(pdf_bytes)

        if not raw_text.strip():
            # Image-based PDF — use vision
            return _parse_pdf_via_vision(pdf_bytes, client)

        raw_text = raw_text[:12000]
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this menu:\n\n{raw_text}"},
        ]
        parsed_dict = client.get_json_completion(messages)
        return ParsedMenu.model_validate(parsed_dict)

    # --- URL path ---
    raw_text = extract_text_from_url(url)
    if not raw_text.strip():
        raise ValueError("Could not extract any text from the provided URL.")

    raw_text = raw_text[:12000]
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Parse this menu:\n\n{raw_text}"},
    ]
    parsed_dict = client.get_json_completion(messages)
    return ParsedMenu.model_validate(parsed_dict)


def _parse_pdf_via_vision(pdf_bytes: bytes, client: LLMClient) -> ParsedMenu:
    """
    Parse an image-based PDF by rendering pages and sending to the vision API.
    For multi-page PDFs, parses each page and merges the results.
    """
    page_images = render_pdf_pages_as_images(pdf_bytes, max_pages=4, resolution=100)

    if not page_images:
        raise ValueError("Could not render any pages from the PDF.")

    _VISION_PROMPT = (
        "This is a restaurant menu image. Extract every dish with its per-serving ingredient "
        "quantities and an estimated number of servings sold per day at a mid-size restaurant "
        "(~150 covers/day).\n\n"
        "Return ONLY a JSON object — no markdown, no explanation:\n\n"
        '{"dishes": [{"name": "string", "description": "string or null", '
        '"category": "string or null", "servings_per_day": integer, '
        '"ingredients": [{"name": "string (lowercase)", '
        '"quantity_per_serving": number or null, "unit": "string or null", "notes": "string or null"}]}]}\n\n'
        "Rules: ingredient names lowercase and canonical. "
        "quantity_per_serving is the amount used in ONE serving of that dish. "
        "servings_per_day is how many times this dish is ordered daily."
    )

    all_dishes = []
    for img_bytes in page_images:
        result = client.get_vision_json_completion(
            image_bytes=img_bytes,
            prompt=_VISION_PROMPT,
            mime_type="image/png",
        )
        dishes = result.get("dishes", [])
        all_dishes.extend(dishes)

    return ParsedMenu.model_validate({"dishes": all_dishes})
