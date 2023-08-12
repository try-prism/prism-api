import secrets

import boto3
from constants import COGNITO_USER_POOL_ID
from exceptions import PrismIdentityException, PrismIdentityExceptionCode
from loguru import logger
from services import SESService


class CognitoService:
    """https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html"""

    def __init__(self):
        self.client = boto3.client("cognito-idp")

    def create_user(
        self, user_id: str, user_email: str, user_name: str, organization_id: str
    ) -> None:
        random_password = secrets.token_urlsafe(15)
        logger.info(
            "user_id={}, user_email={}, user_name={}, organization_id={}, random_password={}",
            user_id,
            user_email,
            user_name,
            organization_id,
            random_password,
        )

        try:
            self.client.admin_create_user(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=user_id,
                UserAttributes=[
                    {"Name": "email", "Value": user_email},
                    {"Name": "custom:name", "Value": user_name},
                    {"Name": "custom:organization_id", "Value": organization_id},
                ],
                TemporaryPassword=random_password,
                MessageAction="SUPPRESS",
                DesiredDeliveryMediums=["EMAIL"],
            )
        except Exception as e:
            logger.error(
                "user_id={}, user_email={}, user_name={}, organization_id={} error={}",
                user_id,
                user_email,
                user_name,
                organization_id,
                str(e),
            )
            raise PrismIdentityException(
                code=PrismIdentityExceptionCode.FAIL_CREATE_USER,
                message="Failed to create user",
            )

        ses_service = SESService()
        ses_service.send_temp_password_email(
            org_user_email=user_email, temp_password=random_password
        )

    def remove_user(self, user_id: str) -> None:
        logger.info("user_id: {}", user_id)

        try:
            self.client.admin_delete_user(
                UserPoolId=COGNITO_USER_POOL_ID, Username=user_id
            )
        except Exception as e:
            logger.error("user_id={}, error={}", user_id, str(e))
            raise PrismIdentityException(
                code=PrismIdentityExceptionCode.FAIL_DELETE_USER,
                message="Failed to delete user",
            )
