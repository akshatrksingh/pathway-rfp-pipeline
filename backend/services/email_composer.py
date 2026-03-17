"""
RFP email composer.

Drafts a professional request-for-proposal email for each distributor,
listing only the ingredients that distributor covers with monthly quantities
and a quote deadline two weeks out.
"""

from datetime import date, timedelta

from services.llm_client import LLMClient


def _quote_deadline() -> str:
    deadline = date.today() + timedelta(weeks=2)
    return deadline.strftime("%B %d, %Y")


def compose_rfp_email(
    restaurant_name: str,
    restaurant_city: str,
    restaurant_state: str,
    distributor_name: str,
    distributor_specialty: str | None,
    ingredients: list[dict],  # [{"name": str, "quantity": float|None, "unit": str|None}]
) -> dict:
    """
    Draft an RFP email via LLM.

    Returns {"subject": str, "body": str}.
    """
    deadline = _quote_deadline()

    # Build ingredient list text for the prompt
    ing_lines = []
    for ing in ingredients:
        qty_str = ""
        if ing.get("quantity"):
            qty_str = f" — {ing['quantity']:.1f} {ing.get('unit') or 'units'}/month"
        ing_lines.append(f"  • {ing['name']}{qty_str}")
    ing_block = "\n".join(ing_lines) if ing_lines else "  • (see attached)"

    specialty_note = f" (specialty: {distributor_specialty})" if distributor_specialty else ""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional procurement writer for a restaurant group. "
                "Draft a concise, business-appropriate Request for Proposal (RFP) email "
                "to a wholesale food distributor. "
                "Tone: professional but friendly. Length: 150–250 words. "
                "Do NOT fabricate prices, minimum orders, or contract terms. "
                "Return ONLY valid JSON with keys 'subject' and 'body'. "
                "The body should be plain text (no markdown, no bullet symbols other than dashes)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Restaurant: {restaurant_name}, located in {restaurant_city}, {restaurant_state}\n"
                f"Distributor: {distributor_name}{specialty_note}\n"
                f"Quote deadline: {deadline}\n\n"
                f"Ingredients needed (monthly quantities):\n{ing_block}\n\n"
                "Draft the RFP email. The subject should be specific and professional. "
                "The body should introduce the restaurant, request pricing for the listed "
                "ingredients, mention the quote deadline, and provide a clear call to action."
            ),
        },
    ]

    client = LLMClient()

    for _attempt in range(2):
        try:
            result = client.get_json_completion(messages)
            subject = result.get("subject") or ""
            body = result.get("body") or ""
            if subject and body:
                return {"subject": subject, "body": body}
        except Exception:
            pass

    # Fallback template — never silently fails
    subject = f"RFP: Wholesale Supply Inquiry — {restaurant_name}"
    body = _fallback_body(restaurant_name, restaurant_city, restaurant_state, distributor_name, ingredients, deadline)
    return {"subject": subject, "body": body}


def _fallback_body(
    restaurant_name: str,
    city: str,
    state: str,
    distributor_name: str,
    ingredients: list[dict],
    deadline: str,
) -> str:
    lines = [
        f"Dear {distributor_name} Team,",
        "",
        f"We are writing on behalf of {restaurant_name} ({city}, {state}) to request "
        f"wholesale pricing for the following ingredients:",
        "",
    ]
    for ing in ingredients:
        qty = f"{ing['quantity']:.1f} {ing.get('unit') or 'units'}/month" if ing.get("quantity") else "quantity TBD"
        lines.append(f"  - {ing['name']}: {qty}")
    lines += [
        "",
        f"Please send your proposal, including unit pricing and delivery terms, by {deadline}.",
        "",
        "Thank you for your time. We look forward to hearing from you.",
        "",
        f"Best regards,",
        f"{restaurant_name} Procurement Team",
    ]
    return "\n".join(lines)


def rewrite_email_with_instruction(
    subject: str,
    body: str,
    instruction: str,
) -> dict:
    """
    Apply a natural-language edit instruction to an existing email draft.

    Returns {"subject": str, "body": str}.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert email editor. Apply the user's edit instruction to "
                "the given email draft. Preserve the professional tone and all factual "
                "content unless the instruction explicitly changes it. "
                "Return ONLY valid JSON with keys 'subject' and 'body'. "
                "The body should be plain text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Current subject: {subject}\n\n"
                f"Current body:\n{body}\n\n"
                f"Edit instruction: {instruction}\n\n"
                "Return the revised email."
            ),
        },
    ]

    client = LLMClient()
    result = client.get_json_completion(messages)

    return {
        "subject": result.get("subject") or subject,
        "body": result.get("body") or body,
    }
