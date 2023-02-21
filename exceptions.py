class AmbiguousException(Exception):
    """Нестандартное исключение."""

    pass


class KeyNotFoundException(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""

    pass


class UnreachableEndpoint(Exception):
    """Недоступность эндпоинта."""

    pass
