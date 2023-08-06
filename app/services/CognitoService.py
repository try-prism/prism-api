import logging

import boto3

logger = logging.getLogger(__name__)


class CognitoService:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html"""

    def __init__(self):
        self.client = boto3.client("cognito-idp")

    def remove_user(self, user_id: str):
        pass
