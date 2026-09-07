from fastapi import HTTPException, status

class VerveGateException(HTTPException):
    """Base exception for all Verve Gate custom errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class DuplicateEmailException(VerveGateException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

class InvalidCredentialsException(VerveGateException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password provided."
        )

class DatabaseOperationException(VerveGateException):
    def __init__(self, message: str = "A database error occurred."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
class InvalidCurrencyException(VerveGateException):
    def __init__(self, currency: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The currency pair '{currency}' is not supported or invalid."
        )

class PaymentProcessingException(VerveGateException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {message}"
        )

class RateProviderException(VerveGateException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live conversion rates are temporarily unavailable. Please try again shortly.",
        )