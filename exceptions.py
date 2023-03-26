class NoPracticumTokenError(Exception):
    """PRACTICUM-TOKEN var is unavailable."""
    pass


class NoTelegramTokenError(Exception):
    """TELEGRAM_TOKEN var is unavailable."""
    pass


class NoTelegamChatIdError(Exception):
    """TELEGRAM_CHAT_ID var is unavailable."""
    pass


class InvalidPracticumTokenError(Exception):
    """PRACTICUM-TOKEN var is invalid."""
    pass


class TimestampArgumentTypeError(TypeError):
    """Unexpected timestamp argument type."""
    pass


class ResponseArgumentTypeError(TypeError):
    """Unexpected response argument type."""
    pass


class HomeworksFieldTypeError(TypeError):
    """Homeworks field type in the API response is invalid."""
    pass


class APIUrlResponseError(Exception):
    """Unexpected API URL response."""
    pass


class UnexpectedHomeworkStatusError(Exception):
    """Unexpected homeworks status."""
    pass


class HomeworkArgumentTypeError(TypeError):
    """Unexpected homework argument type."""
    pass
