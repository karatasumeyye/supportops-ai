from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


async def app_error_handler( request: Request,exception: AppError,) -> JSONResponse:

    return JSONResponse(
        status_code=exception.status_code,
        content={
            "detail": exception.message,
        },
    )


def register_exception_handlers(application: FastAPI) -> None:

    application.add_exception_handler(
        AppError,
        app_error_handler,
    )