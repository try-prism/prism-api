import sys
from http import HTTPStatus

from api.v1 import (
    integration_router,
    organization_router,
    query_router,
    sync_router,
    user_router,
)
from exceptions import PrismException
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS!UTC}</green> "
        "| <level>{level: <5}</level> | <cyan>{file}</cyan>:<cyan>{line}</cyan> "
        "<yellow>{function}</yellow> - <level>{message}</level>"
    ),
    level="INFO",
)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PrismException)
async def prism_api_exception_handler(request: Request, e: PrismException):
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST.value,
        content={"code": e.code.value, "message": e.message},
    )


@app.get("/")
async def root() -> dict:
    return {"message": "Working"}


def prism_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Prism AI API",
        version="1.0.0",
        summary="Python backend of Prism AI built with FastAPI",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = prism_openapi
app.include_router(integration_router, prefix="/v1")
app.include_router(organization_router, prefix="/v1")
app.include_router(query_router, prefix="/v1")
app.include_router(sync_router, prefix="/v1")
app.include_router(user_router, prefix="/v1")
