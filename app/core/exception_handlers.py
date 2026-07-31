from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.exceptions import AppError


async def app_error_handler(
    request: Request,
    exception: AppError,
) -> JSONResponse:

    return JSONResponse(
        status_code=exception.status_code,
        content={
            "detail": exception.message,
        },
    )


def register_exception_handlers(application: FastAPI) -> None:
    handler = cast(
        Callable[[Request, Exception], Response | Awaitable[Response]],
        app_error_handler,
    )

    application.add_exception_handler(
        AppError,
        handler,
    )
