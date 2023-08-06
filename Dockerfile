FROM python:3.10 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Set environment variables
ENV OPENAI_API_KEY=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
ENV OPENAI_ORG_KEY=org-AnMZZ5YjRzyIXkSYH5CtI7FW
ENV DEFAULT_OPENAI_MODEL=gpt-3.5-turbo

ENV AWS_ACCESS_KEY_ID=AKIAYYNCMG5OFUFV4K4W
ENV AWS_SECRET_ACCESS_KEY=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
ENV AWS_DEFAULT_REGION=us-east-1

ENV MERGE_API_KEY=kVETYYxpMryPX5daTzzMgjYmHCvF3l-OZ4EqV2nRsECLND0_epR73A

ENV DYNAMODB_USER_TABLE=srv-prism-user
ENV DYNAMODB_FILE_TABLE=srv-prism-file
ENV DYNAMODB_ORGANIZATION_TABLE=srv-prism-organization
ENV DYNAMODB_STORAGE_CONTEXT_TABLE=srv-prism-storage-context
ENV DYNAMODB_WHITELIST_TABLE=srv-prism-whitelist

ENV S3_FILE_BUCKET=srv-prism-file-store

ENV COGNITO_USER_POOL_ID=test-pool-id

ENV ZILLIZ_CLOUD_HOST=tmp-host
ENV ZILLIZ_CLOUD_PORT=tmp-port
ENV ZILLIZ_CLOUD_USER=tmp-user
ENV ZILLIZ_CLOUD_PASSWORD=tmp-password

COPY ./app /app