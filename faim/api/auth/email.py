"""
FAIM Email Service - Resend Integration

Handles sending OTP codes, verification emails, password reset emails.
Uses Resend API (free tier: 100 emails/day).
"""

import logging
import os
import secrets
from typing import Optional

logger = logging.getLogger(__name__)

# Resend API key from environment
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@faimatrix.com")
APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def generate_verification_token() -> str:
    """Generate a secure random token for email verification."""
    return secrets.token_urlsafe(32)


async def send_verification_email(to_email: str, token: str, name: Optional[str] = None) -> bool:
    """
    Send email verification link to user.

    Args:
        to_email: User's email address
        token: Verification token
        name: User's name (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set - skipping email send")
        return False

    try:
        import httpx

        verification_url = f"{APP_URL}/auth/verify-email?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0f1a; color: #e2e8f0; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 40px; border: 1px solid #334155; }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .logo span {{ background: linear-gradient(135deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 28px; font-weight: bold; }}
                h1 {{ color: #f1f5f9; font-size: 24px; margin-bottom: 16px; }}
                p {{ color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #06b6d4, #3b82f6); color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <span>Faimatrix</span>
                </div>
                <h1>Verify your email</h1>
                <p>Hi{f" {name}" if name else ""},</p>
                <p>Thanks for signing up for Faimatrix! Please verify your email address by clicking the button below:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email</a>
                </p>
                <p>Or copy this link: <br><code style="color: #06b6d4; word-break: break-all;">{verification_url}</code></p>
                <p>This link expires in 24 hours.</p>
                <div class="footer">
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                    <p>© 2026 Faimatrix. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": "Verify your Faimatrix account",
                    "html": html_content,
                },
            )

            if response.status_code == 200:
                logger.info(f"Verification email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return False


async def send_password_reset_email(to_email: str, token: str, name: Optional[str] = None) -> bool:
    """
    Send password reset link to user.

    Args:
        to_email: User's email address
        token: Reset token
        name: User's name (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set - skipping email send")
        return False

    try:
        import httpx

        reset_url = f"{APP_URL}/auth/reset-password?token={token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0f1a; color: #e2e8f0; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 40px; border: 1px solid #334155; }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .logo span {{ background: linear-gradient(135deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 28px; font-weight: bold; }}
                h1 {{ color: #f1f5f9; font-size: 24px; margin-bottom: 16px; }}
                p {{ color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #06b6d4, #3b82f6); color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <span>Faimatrix</span>
                </div>
                <h1>Reset your password</h1>
                <p>Hi{f" {name}" if name else ""},</p>
                <p>We received a request to reset your password. Click the button below to set a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>This link expires in 1 hour.</p>
                <div class="footer">
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>© 2026 Faimatrix. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": "Reset your Faimatrix password",
                    "html": html_content,
                },
            )

            if response.status_code == 200:
                logger.info(f"Password reset email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return False


async def send_otp_email(to_email: str, code: str, name: Optional[str] = None) -> bool:
    """
    Send OTP code to user for passwordless login.

    Args:
        to_email: User's email address
        code: 6-digit OTP code
        name: User's name (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set - skipping email send")
        # In dev mode, log the code for testing
        logger.info(f"[DEV] OTP code for {to_email}: {code}")
        return True  # Return True in dev mode so flow continues

    try:
        import httpx

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0f1a; color: #e2e8f0; padding: 40px; margin: 0; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 40px; border: 1px solid #334155; }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .logo span {{ background: linear-gradient(135deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 28px; font-weight: bold; }}
                h1 {{ color: #f1f5f9; font-size: 24px; margin-bottom: 16px; text-align: center; }}
                p {{ color: #94a3b8; line-height: 1.6; margin-bottom: 24px; text-align: center; }}
                .code-container {{ background: #0f172a; border: 2px solid #334155; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0; }}
                .code {{ font-size: 40px; font-weight: bold; letter-spacing: 12px; color: #06b6d4; font-family: 'Courier New', monospace; }}
                .warning {{ color: #f59e0b; font-size: 14px; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <span>Faimatrix</span>
                </div>
                <h1>Your login code</h1>
                <p>Hi{f" {name}" if name else ""},</p>
                <p>Enter this code to sign in to your Faimatrix account:</p>
                <div class="code-container">
                    <div class="code">{code}</div>
                </div>
                <p class="warning">⏱️ This code expires in 5 minutes.</p>
                <p>If you didn't request this code, you can safely ignore this email.</p>
                <div class="footer">
                    <p>For security, never share this code with anyone.</p>
                    <p>© 2026 Faimatrix. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": f"{code} is your Faimatrix login code",
                    "html": html_content,
                },
            )

            if response.status_code == 200:
                logger.info(f"OTP email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send OTP email: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        logger.error(f"Error sending OTP email: {e}")
        return False
