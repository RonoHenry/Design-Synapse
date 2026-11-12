"""
Custom exceptions for Vendor Service.

This module defines service-specific exceptions for better error handling.
"""

from typing import Any, Dict, Optional


class VendorServiceException(Exception):
    """Base exception for vendor service errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or "VENDOR_SERVICE_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class VendorNotFoundException(VendorServiceException):
    """Raised when a vendor is not found."""

    def __init__(self, vendor_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vendor with ID {vendor_id} not found",
            error_code="VENDOR_NOT_FOUND",
            details=details or {"vendor_id": vendor_id},
        )


class ProductNotFoundException(VendorServiceException):
    """Raised when a product is not found."""

    def __init__(self, product_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Product with ID {product_id} not found",
            error_code="PRODUCT_NOT_FOUND",
            details=details or {"product_id": product_id},
        )


class OrderNotFoundException(VendorServiceException):
    """Raised when an order is not found."""

    def __init__(self, order_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Order with ID {order_id} not found",
            error_code="ORDER_NOT_FOUND",
            details=details or {"order_id": order_id},
        )


class InsufficientInventoryException(VendorServiceException):
    """Raised when product inventory is insufficient."""

    def __init__(
        self,
        product_id: int,
        requested: int,
        available: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Insufficient inventory for product {product_id}. Requested: {requested}, Available: {available}",
            error_code="INSUFFICIENT_INVENTORY",
            details=details
            or {
                "product_id": product_id,
                "requested_quantity": requested,
                "available_quantity": available,
            },
        )


class VendorNotVerifiedException(VendorServiceException):
    """Raised when attempting operations that require vendor verification."""

    def __init__(self, vendor_id: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vendor {vendor_id} is not verified",
            error_code="VENDOR_NOT_VERIFIED",
            details=details or {"vendor_id": vendor_id},
        )


class InvalidOrderStatusException(VendorServiceException):
    """Raised when an invalid order status transition is attempted."""

    def __init__(
        self,
        order_id: int,
        current_status: str,
        requested_status: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Cannot transition order {order_id} from {current_status} to {requested_status}",
            error_code="INVALID_ORDER_STATUS",
            details=details
            or {
                "order_id": order_id,
                "current_status": current_status,
                "requested_status": requested_status,
            },
        )


class UnauthorizedVendorAccessException(VendorServiceException):
    """Raised when a user attempts unauthorized access to vendor resources."""

    def __init__(
        self, user_id: int, vendor_id: int, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"User {user_id} is not authorized to access vendor {vendor_id}",
            error_code="UNAUTHORIZED_VENDOR_ACCESS",
            details=details or {"user_id": user_id, "vendor_id": vendor_id},
        )


class DuplicateVendorException(VendorServiceException):
    """Raised when attempting to create a duplicate vendor."""

    def __init__(self, identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vendor with identifier '{identifier}' already exists",
            error_code="DUPLICATE_VENDOR",
            details=details or {"identifier": identifier},
        )


class InvalidProductDataException(VendorServiceException):
    """Raised when product data validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, error_code="INVALID_PRODUCT_DATA", details=details
        )


class PaymentProcessingException(VendorServiceException):
    """Raised when payment processing fails."""

    def __init__(
        self, order_id: int, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Payment processing failed for order {order_id}: {reason}",
            error_code="PAYMENT_PROCESSING_FAILED",
            details=details or {"order_id": order_id, "reason": reason},
        )
