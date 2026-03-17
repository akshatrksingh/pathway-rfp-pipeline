"""
Menu parser service.

Dispatch:
  - PDF  → pdfplumber text extraction → LLM text parse
         → vision fallback if text is empty (scanned / image-based PDF)
  - Image (PNG/JPG) → direct LLM vision parse
"""

import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import pdfplumber

from schemas import ParsedMenu
from services.llm_client import LLMClient

_TEXT_SYSTEM_PROMPT = """\
You are a restaurant menu parser. Given raw menu text, extract every dish with its \
per-serving ingredient quantities and an estimated number of servings sold per day at \
a mid-size restaurant (~150 covers/day).

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
- Ingredient names must be canonical and lowercase (e.g. 'mozzarella').
- quantity_per_serving is the amount used in ONE serving of that dish.
- servings_per_day is your estimate of daily orders at a busy mid-size restaurant.
- Do not include non-food items.
"""

_VISION_PROMPT = (
    "This is a restaurant menu image. Extract every dish with its per-serving ingredient "
    "quantities and an estimated number of servings sold per day at a mid-size restaurant "
    "(~150 covers/day).\n\n"
    "Return ONLY a JSON object — no markdown, no explanation:\n\n"
    '{"dishes": [{"name": "string", "description": "string or null", '
    '"category": "string or null", "servings_per_day": integer, '
    '"ingredients": [{"name": "string (lowercase)", '
    '"quantity_per_serving": number or null, "unit": "string or null", '
    '"notes": "string or null"}]}]}\n\n'
    "Rules: ingredient names lowercase and canonical. "
    "quantity_per_serving is the amount in ONE serving. "
    "servings_per_day is the estimated daily orders."
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)


def _render_pdf_pages(pdf_bytes: bytes, max_pages: int = 4, resolution: int = 72) -> list[bytes]:
    """Render PDF pages as PNG bytes for vision parsing."""
    images = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:max_pages]:
            buf = io.BytesIO()
            page.to_image(resolution=resolution).original.save(buf, format="PNG")
            images.append(buf.getvalue())
    return images


def _vision_parse(image_bytes: bytes, mime_type: str, client: LLMClient) -> dict:
    return client.get_vision_json_completion(
        image_bytes=image_bytes,
        prompt=_VISION_PROMPT,
        mime_type=mime_type,
    )


def parse_menu(*, file_bytes: bytes, content_type: str) -> ParsedMenu:
    """
    Parse a menu file. content_type determines the strategy:
      - application/pdf  → text extraction, vision fallback for scanned PDFs
      - image/*          → direct vision parse
    """
    client = LLMClient()

    if content_type == "application/pdf":
        text = _extract_pdf_text(file_bytes)

        if not text.strip():
            # Scanned / image-based PDF — render pages and use vision in parallel
            page_images = _render_pdf_pages(file_bytes)
            if not page_images:
                raise ValueError("Could not extract content from this PDF.")

            all_dishes: list[dict] = []
            # Parse pages concurrently — each call is independent
            with ThreadPoolExecutor(max_workers=len(page_images)) as pool:
                futures = {
                    pool.submit(_vision_parse, img_bytes, "image/png", LLMClient()): i
                    for i, img_bytes in enumerate(page_images)
                }
                # Collect results in page order
                ordered: dict[int, list] = {}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        ordered[idx] = result.get("dishes", [])
                    except Exception:
                        ordered[idx] = []
            for i in sorted(ordered):
                all_dishes.extend(ordered[i])
            return ParsedMenu.model_validate({"dishes": all_dishes})

        # Text-based PDF
        messages = [
            {"role": "system", "content": _TEXT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this menu:\n\n{text[:12000]}"},
        ]
        return ParsedMenu.model_validate(client.get_json_completion(messages))

    else:
        # Direct image file (PNG, JPG, etc.)
        result = _vision_parse(file_bytes, content_type, client)
        return ParsedMenu.model_validate(result)
