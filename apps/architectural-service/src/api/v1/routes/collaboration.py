"""Collaboration API routes."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (APIRouter, Depends, HTTPException, Query, WebSocket,
                     WebSocketDisconnect, status)
from pydantic import BaseModel, Field
from src.api.v1.schemas.base import BaseSchema
from src.core.exceptions import NotFoundError
from src.services.collaboration_service import (CollaborationService,
                                                DesignChange)

logger = logging.getLogger(__name__)

router = APIRouter()

# Global collaboration service instance
collaboration_service = CollaborationService()


class CollaborationSessionResponse(BaseSchema):
    """Response schema for collaboration session."""

    session_id: str = Field(..., description="Collaboration session ID")
    design_id: str = Field(..., description="Associated design ID")
    active_users: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of active users"
    )
    websocket_url: str = Field(
        ..., description="WebSocket URL for real-time collaboration"
    )
    is_active: bool = Field(..., description="Whether the session is active")


class JoinSessionRequest(BaseModel):
    """Request schema for joining a collaboration session."""

    user_id: str = Field(..., description="User ID joining the session")
    username: str = Field(..., description="Username for display")


@router.post(
    "/designs/{design_id}/collaboration/join",
    response_model=CollaborationSessionResponse,
)
async def join_collaboration_session(
    design_id: UUID, request: JoinSessionRequest
) -> CollaborationSessionResponse:
    """
    Join or create a collaboration session for a design.

    Args:
        design_id: The design document ID
        request: Join session request data

    Returns:
        CollaborationSessionResponse: Session information including WebSocket URL

    Raises:
        HTTPException: If design not found or other errors
    """
    try:
        session = await collaboration_service.create_session(
            design_id=design_id, user_id=request.user_id, username=request.username
        )

        return CollaborationSessionResponse(
            session_id=session.id,
            design_id=session.design_id,
            active_users=session.active_users or [],
            websocket_url=f"/api/v1/collaboration/{session.id}/ws",
            is_active=session.is_active,
        )

    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error joining collaboration session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join collaboration session",
        )


@router.websocket("/collaboration/{session_id}/ws")
async def websocket_collaboration_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(..., description="User ID for the WebSocket connection"),
    username: str = Query(..., description="Username for display"),
):
    """
    WebSocket endpoint for real-time collaboration.

    Handles:
    - Connection establishment and user joining
    - Design change broadcasting
    - Cursor position updates
    - User disconnect handling
    - Heartbeat for connection monitoring

    Args:
        websocket: WebSocket connection
        session_id: Collaboration session ID
        user_id: User ID connecting
        username: Username for display
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection accepted for user {user_id} in session {session_id}"
    )

    # Add connection to collaboration service
    await collaboration_service.add_connection(session_id, websocket)

    # Send welcome message with current session state
    try:
        active_users = await collaboration_service.get_session_users(session_id)
        welcome_message = {
            "type": "session_joined",
            "data": {
                "session_id": session_id,
                "user_id": user_id,
                "active_users": [user.to_dict() for user in active_users],
            },
        }
        await websocket.send_text(json.dumps(welcome_message))

        # Notify other users about new connection
        join_change = DesignChange(
            change_type="user_join",
            element_id="session",
            data={"user_id": user_id, "username": username},
            user_id="system",
        )
        await collaboration_service.broadcast_change(
            session_id, join_change, exclude_websocket=websocket
        )

    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")
                message_data = message.get("data", {})

                if message_type == "design_change":
                    # Handle design change
                    change = DesignChange(
                        change_type=message_data.get("change_type", "update"),
                        element_id=message_data.get("element_id", ""),
                        data=message_data.get("data", {}),
                        user_id=user_id,
                    )

                    # Broadcast to other users
                    await collaboration_service.broadcast_change(
                        session_id, change, exclude_websocket=websocket
                    )

                elif message_type == "cursor_move":
                    # Handle cursor position update
                    cursor_position = message_data.get("position", {})
                    await collaboration_service.update_user_cursor(
                        session_id, user_id, cursor_position
                    )

                elif message_type == "heartbeat_response":
                    # Client responded to heartbeat - connection is alive
                    logger.debug(f"Received heartbeat response from user {user_id}")

                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {user_id}")
                error_message = {
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                }
                await websocket.send_text(json.dumps(error_message))

            except Exception as e:
                logger.error(f"Error processing message from user {user_id}: {e}")
                error_message = {
                    "type": "error",
                    "data": {"message": "Failed to process message"},
                }
                await websocket.send_text(json.dumps(error_message))

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected for user {user_id} in session {session_id}"
        )
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Cancel heartbeat task
        heartbeat_task.cancel()

        # Handle disconnection
        await collaboration_service.handle_disconnect(session_id, user_id, websocket)


async def send_heartbeat(websocket: WebSocket, interval: int = 30):
    """
    Send periodic heartbeat messages to keep connection alive.

    Args:
        websocket: WebSocket connection
        interval: Heartbeat interval in seconds
    """
    try:
        while True:
            await asyncio.sleep(interval)

            heartbeat_message = {
                "type": "heartbeat",
                "data": {"timestamp": asyncio.get_event_loop().time()},
            }

            try:
                await websocket.send_text(json.dumps(heartbeat_message))
                logger.debug("Sent heartbeat message")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")
                break

    except asyncio.CancelledError:
        logger.debug("Heartbeat task cancelled")
    except Exception as e:
        logger.error(f"Heartbeat task error: {e}")


@router.get("/collaboration/{session_id}/users")
async def get_session_users(session_id: str):
    """
    Get list of active users in a collaboration session.

    Args:
        session_id: Collaboration session ID

    Returns:
        List of active users with their information
    """
    try:
        users = await collaboration_service.get_session_users(session_id)
        return {
            "session_id": session_id,
            "active_users": [user.to_dict() for user in users],
            "user_count": len(users),
        }
    except Exception as e:
        logger.error(f"Error getting session users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session users",
        )
