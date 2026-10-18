"""Transactional email delivery for Desk Buddy pairing OTPs via Resend."""
from .config import settings


class EmailNotConfigured(RuntimeError):
    pass


def send_pairing_otp(to_email: str, otp: str, device_label: str) -> None:
    """Send a pairing OTP through Resend. API credentials remain server-side."""
    if not settings.resend_configured:
        raise EmailNotConfigured(
            "Email OTP is not configured. Set RESEND_API_KEY and EMAIL_FROM."
        )

    try:
        import resend
    except ImportError as exc:
        raise RuntimeError("The Resend package is not installed. Install gateway/requirements.txt.") from exc

    resend.api_key = settings.resend_api_key
    ttl_minutes = max(1, settings.otp_ttl_seconds // 60)
    safe_label = (
        device_label.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
    html = (
        "<div style='font-family:Arial,sans-serif;line-height:1.5'>"
        "<h2>Your Desk Buddy verification code</h2>"
        f"<p>Your code is <strong style='font-size:24px;letter-spacing:4px'>{otp}</strong>.</p>"
        f"<p>This code expires in {ttl_minutes} minute(s).</p>"
        f"<p>Device: {safe_label}</p>"
        "<p>If you did not request this code, you can ignore this email.</p>"
        "</div>"
    )
    resend.Emails.send({
        "from": settings.email_from,
        "to": [to_email],
        "subject": "Your Desk Buddy verification code",
        "html": html,
        "text": (
            f"Your Desk Buddy code is {otp}. It expires in {ttl_minutes} minute(s).\n\n"
            f"Device: {device_label}\n\n"
            "If you did not request this code, ignore this email."
        ),
    })
