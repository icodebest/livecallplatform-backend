import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import Settings
from app.core.logger import logger


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_verification_otp(self, email: str, otp: str) -> None:
        await self.send_otp(email, otp, "Verify your Maya Voice Agent account", "Your verification code")

    async def send_password_reset_otp(self, email: str, otp: str) -> None:
        await self.send_otp(email, otp, "Reset your Maya Voice Agent password", "Your password reset code")

    async def send_otp(self, email: str, otp: str, subject: str, label: str) -> None:
        if not self.settings.smtp_host or not self.settings.email_from:
            logger.info("%s for %s: %s", label, email, otp)
            return
        await asyncio.to_thread(self._send, email, otp, subject, label)

    def _send(self, email: str, otp: str, subject: str, label: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.email_from
        message["To"] = email
        message.set_content(f"{label} is {otp}. It expires in 15 minutes.")

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(message)
