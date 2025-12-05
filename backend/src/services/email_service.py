import os
import resend
from loguru import logger
from dotenv import load_dotenv
import asyncio
import requests

load_dotenv()

resend.api_key = "re_SMutgeWp_3aVdrY5NmdVztr7TVvv6MQB2"


class MailService:
    def send_signup_email(self, to: str, verification_url: str):
        try:
            params = {
                "from": "onboarding@resend.dev",
                "to": [to],
                "subject": "Verify Sign Up Email",
                "html": f"<p>{verification_url}</p>",
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
                "html": f"<p>lease click this link to reset your password: {verification_url}</p>",
            }
            result = resend.Emails.send(params)
            return result

        except Exception as e:
            logger.error(f"An error occurred while sending email: {e}")
            return None 



    def send_invite_email(self, to: str, invite_url: str):
        try:
            params = {
                "from": "noreply@support.suryaweb.app",
                "to": [to],
                "subject": "User Invite Email",
                "html": f"<p>Please click this to accept the invitation.{invite_url}</p>",
            }
            result = resend.Emails.send(params)
            return result

        except Exception as e:
            logger.error(f"An error occurred while sending email: {e}")
            return None        
 