import resend
from loguru import logger

from core.config import settings


class MailService:
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY

    def send_signup_email(self, to: str, verification_url: str, username: str = "User"):
        try:
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; padding: 40px 20px;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden;">
                                <tr>
                                    <td style="padding: 40px 40px 20px 40px;">
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #111827;">Tone</h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 20px 40px;">
                                        <div style="width: 120px; height: 100px; position: relative;">
                                            <div style="background-color: #F5C842; border-radius: 0 0 16px 16px; width: 100px; height: 60px; margin: 30px auto 0 auto;"></div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 20px 40px 10px 40px;">
                                        <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #111827;">Hi! {username}</h2>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 0 40px 10px 40px;">
                                        <h3 style="margin: 0; font-size: 20px; font-weight: 600; color: #111827;">Welcome to Tone</h3>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 0 40px 30px 40px;">
                                        <p style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.6; max-width: 400px;">
                                            Tone helps you manage your organization efficiently with powerful tools for team collaboration and productivity.
                                        </p>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 0 40px 40px 40px;">
                                        <a href="{verification_url}" style="display: inline-block; background-color: #111827; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 14px; font-weight: 500;">
                                            Confirm your Email
                                        </a>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding: 0 40px 40px 40px;">
                                        <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                                            If you didn't create an account, you can safely ignore this email.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            params = {
                "from": "no-reply@updates.suryaweb.app",
                "to": [to],
                "subject": "Verify your Tone account",
                "html": html_template,
            }
            result = resend.Emails.send(params)
            return result

        except Exception as e:
            logger.error(f"An error occurred while sending email: {e}")
            return None

    def send_forgot_password_email(self, to: str, verification_url: str):
        try:
            params = {
                "from": "no-reply@updates.suryaweb.app",
                "to": [to],
                "subject": "Forgot Password Email",
                "html": f'<p>Please click this link to reset your password: <a href="{verification_url}">{verification_url}</a></p>',
            }
            result = resend.Emails.send(params)
            return result

        except Exception as e:
            logger.error(f"An error occurred while sending email: {e}")
            return None

    def send_invite_email(self, to: str, invite_url: str):
        try:
            params = {
                "from": "no-reply@updates.suryaweb.app",
                "to": [to],
                "subject": "You've been invited to join Tone",
                "html": f'<p>Please click this to accept the invitation: <a href="{invite_url}">{invite_url}</a></p>',
            }
            result = resend.Emails.send(params)
            return result

        except Exception as e:
            logger.error(f"An error occurred while sending email: {e}")
            return None
