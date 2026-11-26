"""
Custom exception hierarchy for AI providers, authentication, rate limits, and server errors.
"""

class AIException(Exception):
    """Base class for all AI provider exceptions."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.provider = provider


class AIConfigurationError(AIException):
    """
    Raised when an AI provider fails authentication (e.g. invalid API key, unauthenticated, 401/403).
    Must NOT trigger automatic fallback to subsequent providers.
    """
    pass


class AIRateLimitError(AIException):
    """
    Raised when an AI provider is quota-exhausted or rate-limited (HTTP 429, ResourceExhausted).
    Triggers automatic fallback to the next provider in the chain.
    """
    pass


class AITemporaryServerError(AIException):
    """
    Raised on transient upstream server errors (HTTP 502, 503, 504, Bad Gateway, Service Unavailable).
    Triggers automatic fallback to the next provider in the chain.
    """
    pass
