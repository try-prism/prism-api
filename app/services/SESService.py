import boto3
from constants import REGISTER_URL, SES_SENDER_EMAIL
from exceptions import PrismEmailException, PrismEmailExceptionCode
from loguru import logger


class SESService:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html"""

    def __init__(self):
        self.client = boto3.client("ses")

    def send_signup_email(
        self, org_name: str, org_user_email: str, org_user_id: str
    ) -> None:
        logger.info(
            "org_name={}, user_email={}, org_user_id={}",
            org_name,
            org_user_email,
            org_user_id,
        )

        try:
            response = self.client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={
                    "ToAddresses": [
                        org_user_email,
                    ],
                    "CcAddresses": [],
                    "BccAddresses": [],
                },
                Message={
                    "Subject": {
                        "Charset": "UTF-8",
                        "Data": f"[Prism AI] {org_name} invited to join the workspace",
                    },
                    "Body": {
                        "Text": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"You have been invited to join the {org_name} workspace."
                                f"Click here to sign up.\n{REGISTER_URL + org_user_id}"
                            ),
                        },
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"<p>You have been invited to join the {org_name} workspace.</p>"
                                f'<p><a href="{REGISTER_URL + org_user_id}" target="_blank">'
                                f"Click here to sign up</a></p>"
                            ),
                        },
                    },
                },
                ReplyToAddresses=[],
            )
        except Exception as e:
            logger.error(
                "org_name={}, org_user_email={}, org_user_id={}, error={}",
                org_name,
                org_user_email,
                org_user_id,
                str(e),
            )
            raise PrismEmailException(
                code=PrismEmailExceptionCode.SIGNUP_EMAIL_NOT_SENT,
                message="Failed to send signup email",
            )

        logger.info(
            "org_name={}, org_user_email={}, org_user_id={}, response={}",
            org_name,
            org_user_email,
            org_user_id,
            response,
        )

    def send_temp_password_email(self, org_user_email: str, temp_password: str) -> None:
        logger.info(
            "org_user_email={}, temp_password={}", org_user_email, temp_password
        )

        try:
            response = self.client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={
                    "ToAddresses": [
                        org_user_email,
                    ],
                    "CcAddresses": [],
                    "BccAddresses": [],
                },
                Message={
                    "Subject": {
                        "Charset": "UTF-8",
                        "Data": "[Prism AI] Your temporary password",
                    },
                    "Body": {
                        "Text": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"Your temporary password is {temp_password}"
                                f"Please change your password after logging in."
                            ),
                        },
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"Your temporary password is {temp_password}"
                                f"Please change your password after logging in."
                            ),
                        },
                    },
                },
                ReplyToAddresses=[],
            )
        except Exception as e:
            logger.info(
                "org_user_email={}, temp_password={}, error={}",
                org_user_email,
                temp_password,
                e,
            )
            raise PrismEmailException(
                code=PrismEmailExceptionCode.TEMP_PW_EMAIL_NOT_SENT,
                message="Failed to send temporary password email",
            )

        logger.info(
            "org_user_email={}, temp_password={}, response={}",
            org_user_email,
            temp_password,
            response,
        )
