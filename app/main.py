# Standard Library
import logging

from api.v1.corporate import router as corporate_router
from api.v1.document import router as document_router
from api.v1.integration import router as integration_router
from api.v1.query import router as query_router
from api.v1.user import router as user_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

log_format = (
    "%(asctime)s::%(levelname)s::%(name)s::" "%(filename)s::%(lineno)d::%(message)s"
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
app.include_router(corporate_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(integration_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
