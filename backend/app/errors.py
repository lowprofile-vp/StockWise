class APIError(Exception):
    """Expected request failure with a message safe to show in the UI."""

    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details
