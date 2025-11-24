"""
Custom Exceptions for Labor Services Marketplace

Defines application-specific exceptions for better error handling
and user experience.
"""

from typing import Optional, Dict, Any


class LaborServiceException(Exception):
    """Base exception for Labor Service"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(LaborServiceException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field


class NotFoundError(LaborServiceException):
    """Raised when a requested resource is not found"""
    
    def __init__(self, resource: str, identifier: Any, **kwargs):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(message, error_code="NOT_FOUND", **kwargs)
        self.resource = resource
        self.identifier = identifier


class AuthenticationError(LaborServiceException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(LaborServiceException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


# Alias for consistency with other services
UnauthorizedError = AuthorizationError


class BusinessLogicError(LaborServiceException):
    """Raised when business logic constraints are violated"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="BUSINESS_LOGIC_ERROR", **kwargs)


class ExternalServiceError(LaborServiceException):
    """Raised when external service calls fail"""
    
    def __init__(self, service: str, message: str, **kwargs):
        full_message = f"External service '{service}' error: {message}"
        super().__init__(full_message, error_code="EXTERNAL_SERVICE_ERROR", **kwargs)
        self.service = service


class DatabaseError(LaborServiceException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)


# Provider-specific exceptions
class ProviderNotFoundError(NotFoundError):
    """Raised when a service provider is not found"""
    
    def __init__(self, provider_id: Any):
        super().__init__("ServiceProvider", provider_id)


class ProviderNotVerifiedError(BusinessLogicError):
    """Raised when attempting operations with unverified provider"""
    
    def __init__(self, provider_id: Any):
        super().__init__(f"Provider {provider_id} is not verified")


class ProviderUnavailableError(BusinessLogicError):
    """Raised when provider is not available for requested time"""
    
    def __init__(self, provider_id: Any, requested_time: str):
        super().__init__(f"Provider {provider_id} is not available at {requested_time}")


# Request-specific exceptions
class ServiceRequestNotFoundError(NotFoundError):
    """Raised when a service request is not found"""
    
    def __init__(self, request_id: Any):
        super().__init__("ServiceRequest", request_id)


class ServiceRequestClosedError(BusinessLogicError):
    """Raised when attempting to modify a closed service request"""
    
    def __init__(self, request_id: Any):
        super().__init__(f"Service request {request_id} is closed and cannot be modified")


# Quote-specific exceptions
class QuoteNotFoundError(NotFoundError):
    """Raised when a quote is not found"""
    
    def __init__(self, quote_id: Any):
        super().__init__("Quote", quote_id)


class QuoteExpiredError(BusinessLogicError):
    """Raised when attempting to accept an expired quote"""
    
    def __init__(self, quote_id: Any):
        super().__init__(f"Quote {quote_id} has expired")


class QuoteAlreadyAcceptedError(BusinessLogicError):
    """Raised when attempting to accept an already accepted quote"""
    
    def __init__(self, quote_id: Any):
        super().__init__(f"Quote {quote_id} has already been accepted")


# Booking-specific exceptions
class BookingNotFoundError(NotFoundError):
    """Raised when a booking is not found"""
    
    def __init__(self, booking_id: Any):
        super().__init__("Booking", booking_id)


class BookingConflictError(BusinessLogicError):
    """Raised when booking conflicts with existing bookings"""
    
    def __init__(self, provider_id: Any, time_slot: str):
        super().__init__(f"Booking conflict for provider {provider_id} at {time_slot}")


class BookingCancellationError(BusinessLogicError):
    """Raised when booking cannot be cancelled"""
    
    def __init__(self, booking_id: Any, reason: str):
        super().__init__(f"Cannot cancel booking {booking_id}: {reason}")


# Payment-specific exceptions
class PaymentError(LaborServiceException):
    """Raised when payment processing fails"""
    
    def __init__(self, message: str, payment_id: Optional[Any] = None, **kwargs):
        super().__init__(message, error_code="PAYMENT_ERROR", **kwargs)
        self.payment_id = payment_id


class InsufficientFundsError(PaymentError):
    """Raised when payment fails due to insufficient funds"""
    
    def __init__(self, amount: float, **kwargs):
        super().__init__(f"Insufficient funds for payment of ${amount:.2f}", **kwargs)


class EscrowError(PaymentError):
    """Raised when escrow operations fail"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(f"Escrow error: {message}", **kwargs)


# Review-specific exceptions
class ReviewNotFoundError(NotFoundError):
    """Raised when a review is not found"""
    
    def __init__(self, review_id: Any):
        super().__init__("Review", review_id)


class DuplicateReviewError(BusinessLogicError):
    """Raised when attempting to create duplicate review"""
    
    def __init__(self, booking_id: Any, reviewer_id: Any):
        super().__init__(f"Review already exists for booking {booking_id} by user {reviewer_id}")


# Geolocation-specific exceptions
class GeolocationError(LaborServiceException):
    """Raised when geolocation operations fail"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="GEOLOCATION_ERROR", **kwargs)


class InvalidLocationError(GeolocationError):
    """Raised when location data is invalid"""
    
    def __init__(self, location: str):
        super().__init__(f"Invalid location: {location}")


# Matching-specific exceptions
class MatchingError(LaborServiceException):
    """Raised when matching operations fail"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="MATCHING_ERROR", **kwargs)


class NoProvidersFoundError(MatchingError):
    """Raised when no providers match the request criteria"""
    
    def __init__(self, request_id: Any):
        super().__init__(f"No providers found for request {request_id}")


# Rate limiting exceptions
class RateLimitExceededError(LaborServiceException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: int, **kwargs):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)