"""
Email sender — AgentMail with console fallback.

Sender inbox : rfp-pathway@agentmail.to
Recipient    : akshatrksingh+{distributor_slug}@gmail.com
Fallback     : prints to stdout when AGENTMAIL_API_KEY is absent.
"""

import re

from config import get_settings

settings = get_settings()

SENDER_INBOX = "rfp-pathway@agentmail.to"
RECIPIENT_BASE = "akshatrksingh"
RECIPIENT_DOMAIN = "gmail.com"


def _slugify(name: str) -> str:
    """'Sysco Food Services' → 'sysco-food-services'"""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def recipient_for(distributor_name: str) -> str:
    slug = _slugify(distributor_name)
    return f"{RECIPIENT_BASE}+{slug}@{RECIPIENT_DOMAIN}"


def send_rfp_email(
    distributor_name: str,
    subject: str,
    body: str,
) -> dict:
    """
    Send an RFP email to the mock recipient for this distributor.

    Returns {"sent": bool, "message_id": str | None, "recipient": str}.
    """
    recipient = recipient_for(distributor_name)

    if not settings.agentmail_api_key:
        # Console fallback — useful for local dev / demos without an API key
        print("\n" + "=" * 60)
        print(f"[AgentMail FALLBACK] Would send email:")
        print(f"  From   : {SENDER_INBOX}")
        print(f"  To     : {recipient}")
        print(f"  Subject: {subject}")
        print(f"  Body   :\n{body}")
        print("=" * 60 + "\n")
        return {"sent": False, "message_id": None, "recipient": recipient}

    try:
        from agentmail import AgentMail

        client = AgentMail(api_key=settings.agentmail_api_key)
        response = client.inboxes.messages.send(
            SENDER_INBOX,
            to=recipient,
            subject=subject,
            text=body,
        )
        message_id = getattr(response, "message_id", None) or getattr(response, "id", None)
        return {"sent": True, "message_id": str(message_id) if message_id else None, "recipient": recipient}

    except Exception as exc:
        print(f"[AgentMail ERROR] Failed to send to {recipient}: {exc}")
        return {"sent": False, "message_id": None, "recipient": recipient}
