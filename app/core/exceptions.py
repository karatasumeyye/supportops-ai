class AppError(Exception):
    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    default_message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    default_message = "Resource conflict."