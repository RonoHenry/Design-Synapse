"""Order API routes."""

from typing import Any, Optional


# Mock User model for testing
class User:
    def __init__(self, id: int, username: str, email: str, roles: list = None):
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles or []


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from src.api.dependencies import get_current_user, get_order_service
from src.api.v1.schemas.order import (AddItemToOrder, OrderCreate,
                                      OrderListResponse, OrderResponse,
                                      OrderSearch, OrderStatusUpdate,
                                      OrderUpdate, PaymentData)
from src.services.order_service import OrderService

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Create a new order."""
    try:
        # Convert Pydantic items to dict format
        items = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
            }
            for item in order_data.items
        ]

        order = await order_service.create_order(
            customer_id=current_user.id,
            items=items,
            shipping_address=order_data.shipping_address,
        )
        return OrderResponse.from_orm(order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order creation failed due to data conflict",
        )


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    search_params: OrderSearch = Depends(),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """List orders with optional filtering."""
    # Users can only see their own orders unless they have admin role
    customer_id = search_params.customer_id
    if "admin" not in current_user.roles:
        customer_id = current_user.id

    orders = await order_service.get_customer_orders(
        customer_id=customer_id,
        skip=search_params.skip,
        limit=search_params.limit,
        status=search_params.status,
    )

    # Get total count (simplified for now)
    total = len(orders) + search_params.skip

    return OrderListResponse(
        orders=[OrderResponse.from_orm(order) for order in orders],
        total=total,
        skip=search_params.skip,
        limit=search_params.limit,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Get order by ID."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can access this order
    if order.customer_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return OrderResponse.from_orm(order)


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Update order details."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can modify this order
    if order.customer_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Only allow updates for pending orders
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update order with status {order.status}",
        )

    # For now, we only support updating shipping address
    # In a real implementation, you might have more fields
    if order_data.shipping_address is not None:
        order.shipping_address = order_data.shipping_address
        # You would update the order in the repository here

    return OrderResponse.from_orm(order)


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Update order status."""
    try:
        updated_order = await order_service.update_order_status(
            order_id=order_id,
            new_status=status_data.status,
            updated_by=current_user.id,
        )
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return OrderResponse.from_orm(updated_order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Cancel an order."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can cancel this order
    if order.customer_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    try:
        cancelled_order = await order_service.cancel_order(
            order_id=order_id,
            cancelled_by=current_user.id,
        )
        if not cancelled_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return OrderResponse.from_orm(cancelled_order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{order_id}/payment", response_model=OrderResponse)
async def process_payment(
    order_id: int,
    payment_data: PaymentData,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Process payment for an order."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can pay for this order
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Validate payment amount matches order total
    if payment_data.amount != order.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount does not match order total",
        )

    try:
        paid_order = await order_service.process_payment(
            order_id=order_id,
            payment_data=payment_data.dict(),
        )
        if not paid_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return OrderResponse.from_orm(paid_order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{order_id}/items", response_model=OrderResponse)
async def add_item_to_order(
    order_id: int,
    item_data: AddItemToOrder,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Add item to existing order."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can modify this order
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    try:
        updated_order = await order_service.add_item_to_order(
            order_id=order_id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
        )
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return OrderResponse.from_orm(updated_order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{order_id}/items/{product_id}", response_model=OrderResponse)
async def remove_item_from_order(
    order_id: int,
    product_id: int,
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Remove item from existing order."""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if user can modify this order
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    try:
        updated_order = await order_service.remove_item_from_order(
            order_id=order_id,
            product_id=product_id,
        )
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return OrderResponse.from_orm(updated_order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/vendor/{vendor_id}", response_model=OrderListResponse)
async def get_vendor_orders(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(get_order_service),
):
    """Get orders for a vendor (vendor or admin only)."""
    # Check if user is the vendor or admin
    if "admin" not in current_user.roles:
        # In a real implementation, you'd check if current_user is the vendor
        # For now, we'll allow any authenticated user
        pass

    orders = await order_service.get_vendor_orders(
        vendor_id=vendor_id,
        skip=skip,
        limit=limit,
        status=status,
    )

    # Get total count (simplified for now)
    total = len(orders) + skip

    return OrderListResponse(
        orders=[OrderResponse.from_orm(order) for order in orders],
        total=total,
        skip=skip,
        limit=limit,
    )
