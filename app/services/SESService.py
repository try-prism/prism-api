import logging

import boto3
from constants import DEFAULT_SIGNUP_URL, SES_SENDER_EMAIL

logger = logging.getLogger(__name__)


class SESService:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html"""

    def __init__(self):
        self.client = boto3.client("ses")

    def send_signup_email(self, org_name: str, user_email: str, user_id: str) -> bool:
        logger.info(
            f"Sending signup email. org_name={org_name}, user_email={user_email}, user_id={user_id}"
        )

        try:
            response = self.client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={
                    "ToAddresses": [
                        user_email,
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
                                f"Click here to sign up.\n{DEFAULT_SIGNUP_URL + user_id}"
                            ),
                        },
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": (
                                f"<p>You have been invited to join the {org_name} workspace.</p>"
                                f'<p><a href="{DEFAULT_SIGNUP_URL + user_id}" target="_blank">'
                                f"Click here to sign up</a></p>"
                            ),
                        },
                    },
                },
                ReplyToAddresses=[],
            )
            logger.info(
                f"org_name={org_name}, user_email={user_email}, "
                f"user_id={user_id}, response={response}"
            )
        except Exception as e:
            logger.error(
                f"org_name={org_name}, user_email={user_email}, user_id={user_id}, {str(e)}"
            )
            return False

        return True
