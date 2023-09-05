FROM python:3.10 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Set environment variables
ENV OPENAI_API_KEY=YOUR_API_KEY
ENV OPENAI_ORG_KEY=YOUR_ORG_KEY
ENV DEFAULT_OPENAI_MODEL=gpt-3.5-turbo

ENV AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
ENV AWS_DEFAULT_REGION=us-east-1

ENV MERGE_API_KEY=YOUR_MERGE_API_KEY

ENV COHERE_API_KEY=YOUR_COHERE_API_KEY

ENV DYNAMODB_USER_TABLE=srv-prism-user
ENV DYNAMODB_FILE_TABLE=srv-prism-file
ENV DYNAMODB_ORGANIZATION_TABLE=srv-prism-organization
ENV DYNAMODB_WHITELIST_TABLE=srv-prism-whitelist

ENV DYNAMODB_FILE_TABLE_INDEX=account_token-index

ENV COGNITO_USER_POOL_ID=YOUR_AWS_COGNITO_USER_POOL_ID

ENV ZILLIZ_CLOUD_HOST=tmp-host
ENV ZILLIZ_CLOUD_PORT=tmp-port
ENV ZILLIZ_CLOUD_USER=tmp-user
ENV ZILLIZ_CLOUD_PASSWORD=tmp-password

ENV RAY_ADDRESS=ray://<app_name>-ray-head:10001

ENV PRISM_ENV=PROD

EXPOSE 8000

COPY ./app /app
