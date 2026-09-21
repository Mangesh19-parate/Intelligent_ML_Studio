import re
import secrets
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

class EmailService:
    """
    Service for Email validation, OTP generation, and 2FA Email Delivery.
    Zero mandatory external dependencies; seamlessly logs to console in dev/test
    and dispatches via standard SMTP when configured in production.
    """

    @classmethod
    def is_valid_email(cls, email: str | None) -> bool:
        """Validates that an email address follows standard RFC email format."""
        if not email or not isinstance(email, str):
            return False
        clean = email.strip()
        if len(clean) < 5 or len(clean) > 150:
            return False
        if not EMAIL_REGEX.match(clean):
            return False
        parts = clean.split("@")
        if len(parts) != 2:
            return False
        domain = parts[1]
        if "." not in domain or domain.startswith(".") or domain.endswith("."):
            return False
        tld = domain.split(".")[-1]
        if len(tld) < 2:
            return False
        return True

    @classmethod
    def mask_email(cls, email: str) -> str:
        """Masks an email for user-facing security display (e.g. d***@mlstudio.io)."""
        if not email or "@" not in email:
            return email or ""
        user_part, domain = email.split("@", 1)
        if len(user_part) <= 2:
            masked_user = user_part[0] + "***"
        else:
            masked_user = user_part[0] + "***" + user_part[-1]
        return f"{masked_user}@{domain}"

    @classmethod
    def generate_otp(cls, digits: int = 6) -> str:
        """Generates a cryptographically random 6-digit numeric OTP code."""
        min_val = 10 ** (digits - 1)
        max_val = (10 ** digits) - 1
        code_int = secrets.randbelow(max_val - min_val + 1) + min_val
        return str(code_int)

    @classmethod
    def send_otp_email(
        cls,
        to_email: str,
        otp_code: str,
        user_name: str | None = None,
        expire_minutes: int = 10,
    ) -> bool:
        """
        Dispatches the 2FA OTP code to the user's email address.
        Displays a structured visual banner in the console for instant dev/testing verification,
        and optionally sends real SMTP email if SMTP is configured.
        """
        greeting_name = user_name.strip() if user_name else "ML Studio User"
        masked = cls.mask_email(to_email)

        # 1. Output styled notification box in server logs (dev/testing only, disabled in production)
        is_prod = getattr(settings, "ENV", "").lower() == "production"
        if not is_prod:
            border = "═" * 64
            console_banner = (
                f"\n╔{border}╗\n"
                f"║ 🔐 [EMAIL 2FA] TWO-FACTOR VERIFICATION CODE ISSUED           ║\n"
                f"╠{border}╣\n"
                f"║ Recipient : {to_email:<48} ║\n"
                f"║ Masked    : {masked:<48} ║\n"
                f"║ OTP CODE  : >>>  {otp_code}  <<< (Valid for {expire_minutes} minutes)        ║\n"
                f"║ Notice    : Enter this 6-digit code on the Sign In screen.     ║\n"
                f"║             No authenticator app or QR code scan needed.       ║\n"
                f"╚{border}╝\n"
            )
            print(console_banner, flush=True)
        logger.info(f"[EMAIL 2FA] Sent 6-digit OTP code to {masked} (Expires in {expire_minutes}m)")

        # 2. If SMTP is configured in environment, dispatch real email
        smtp_host = getattr(settings, "SMTP_HOST", None) or getattr(settings, "MAIL_SERVER", None)
        if smtp_host:
            try:
                smtp_port = int(getattr(settings, "SMTP_PORT", 587))
                smtp_user = getattr(settings, "SMTP_USER", None) or getattr(settings, "MAIL_USERNAME", None)
                smtp_password = getattr(settings, "SMTP_PASSWORD", None) or getattr(settings, "MAIL_PASSWORD", None)
                from_email = getattr(settings, "EMAILS_FROM_EMAIL", "security@mlstudio.io")
                from_name = getattr(settings, "EMAILS_FROM_NAME", "ML Studio Security")

                subject = f"[ML Studio] Your Verification Code: {otp_code}"
                text_content = (
                    f"Hello {greeting_name},\n\n"
                    f"Your 6-digit two-factor verification code is: {otp_code}\n\n"
                    f"This code will expire in {expire_minutes} minutes. Enter this code on the sign-in page to authenticate your session.\n\n"
                    f"If you did not request this code, please secure your account immediately.\n\n"
                    f"— ML Studio Security Team"
                )

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px 20px;">
                  <div style="max-width: 520px; margin: 0 auto; background-color: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
                    <div style="text-align: center; margin-bottom: 24px;">
                      <h1 style="color: #6366f1; font-size: 24px; margin: 0; font-weight: 800; letter-spacing: -0.5px;">ML Studio</h1>
                      <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Two-Factor Authentication</p>
                    </div>
                    <p style="font-size: 14px; color: #cbd5e1; line-height: 1.5;">Hello <strong>{greeting_name}</strong>,</p>
                    <p style="font-size: 14px; color: #94a3b8; line-height: 1.5;">Please use the following 6-digit verification code to complete your sign in:</p>
                    <div style="background-color: #0f172a; border: 1px solid #4f46e5; border-radius: 12px; padding: 20px; text-align: center; margin: 28px 0;">
                      <span style="font-family: monospace; font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #818cf8;">{otp_code}</span>
                    </div>
                    <p style="font-size: 12px; color: #64748b; line-height: 1.4; text-align: center;">This code expires in <strong>{expire_minutes} minutes</strong>. Do not share this code with anyone.</p>
                  </div>
                </body>
                </html>
                """

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{from_email}>"
                msg["To"] = to_email
                msg.attach(MIMEText(text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    if smtp_user and smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                logger.info(f"[EMAIL 2FA] Successfully sent SMTP email to {to_email}")
            except Exception as e:
                logger.error(f"[EMAIL 2FA] Failed to send SMTP email to {to_email}: {e}")
                return True

        return True
