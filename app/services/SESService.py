import boto3


class SESService:
    def __init__(self):
        self.client = boto3.client("ses")

    def send_signup_email(self, email: str, user_id: str):
        # TODO: Implement send_signup_email
        pass
