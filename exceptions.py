class NoEnvVarError(Exception):
    """One or several environment variables are unavailable."""


class InvalidPracticumTokenError(Exception):
    """PRACTICUM-TOKEN var is invalid."""


class TimestampArgumentTypeError(TypeError):
    """Unexpected timestamp argument type."""


class ResponseArgumentTypeError(TypeError):
    """Unexpected response argument type."""

    pass


class HomeworksFieldTypeError(TypeError):
    """Homeworks field type in the API response is invalid."""


class APIUrlResponseError(Exception):
    """Unexpected API URL response."""


class UnexpectedHomeworkStatusError(Exception):
    """Unexpected homeworks status."""


class HomeworkArgumentTypeError(TypeError):
    """Unexpected homework argument type."""


class APIResponseJSONDecodeError(ValueError):
    """Couldn't decode the API response into json."""


class APIRequestException(Exception):
    """API RequestException."""
