import logging

import boto3
from constants import DEFAULT_SIGNUP_URL, SES_SENDER_EMAIL

logger = logging.getLogger(__name__)


class SESService:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html"""

    def __init__(self):
        self.client = boto3.client("ses")

    def send_signup_email(
        self, org_name: str, org_user_email: str, org_user_id: str
    ) -> bool:
        logger.info(
            "Sending signup email. org_name=%s, user_email=%s, org_user_id=%s",
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
                                f"Click here to sign up.\n{DEFAULT_SIGNUP_URL + org_user_id}"
                            ),
                        },
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"<p>You have been invited to join the {org_name} workspace.</p>"
                                f'<p><a href="{DEFAULT_SIGNUP_URL + org_user_id}" target="_blank">'
                                f"Click here to sign up</a></p>"
                            ),
                        },
                    },
                },
                ReplyToAddresses=[],
            )
            logger.info(
                "org_name=%s, org_user_email=%s, org_user_id=%s, response=%s",
                org_name,
                org_user_email,
                org_user_id,
                response,
            )
        except Exception as e:
            logger.error(
                "org_name=%s, org_user_email=%s, org_user_id=%s, error=%s",
                org_name,
                org_user_email,
                org_user_id,
                str(e),
            )
            return False

        return True
