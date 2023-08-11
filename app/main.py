import logging

from api.v1 import (
    integration_router,
    organization_router,
    query_router,
    sync_router,
    user_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

log_format = (
    "%(asctime)s::%(levelname)s::%(name)s "
    "[%(filename)s::%(lineno)d::%(funcName)20s()] %(message)s"
)
logging.basicConfig(level=logging.INFO, format=log_format)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
