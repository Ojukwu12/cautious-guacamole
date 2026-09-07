import httpx

from app.core.config import settings


async def send_password_reset_email(recipient: str, reset_url: str) -> bool:
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        return False
    payload = {
        "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
        "to": [{"email": recipient}],
        "subject": "Reset your Verve Gate password",
        "htmlContent": (
            "<p>We received a request to reset your Verve Gate password.</p>"
            f"<p><a href=\"{reset_url}\">Reset your password</a></p>"
            f"<p>This link expires in {settings.PASSWORD_RESET_TTL_MINUTES} minutes and can only be used once.</p>"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return True
    except httpx.HTTPError:
        return False
