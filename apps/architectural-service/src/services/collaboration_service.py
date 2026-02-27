"""CollaborationService for real-time collaboration management."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import AsyncSessionLocal
from src.core.exceptions import NotFoundError, ValidationError
from src.models.collaboration_session import CollaborationSession
from src.models.design import Design
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class DesignChange:
    """Represents a design change event."""

    def __init__(
        self,
        change_type: str,
        element_id: str,
        data: Dict[str, Any],
        user_id: str,
        timestamp: Optional[datetime] = None,
    ):
        self.change_type = change_type
        self.element_id = element_id
        self.data = data
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_type": self.change_type,
            "element_id": self.element_id,
            "data": self.data,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
        }


class DesignConflict:
    """Represents a conflict between concurrent design changes."""

    def __init__(
        self,
        element_id: str,
        changes: List[DesignChange],
        conflict_type: str = "concurrent_edit",
    ):
        self.element_id = element_id
        self.changes = changes
        self.conflict_type = conflict_type


class UserInfo:
    """Represents user information in a collaboration session."""

    def __init__(
        self,
        user_id: str,
        username: str,
        cursor_position: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.cursor_position = cursor_position or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "cursor_position": self.cursor_position,
        }


class CollaborationService:
    """Service for managing real-time collaboration sessions."""

    def __init__(self):
        # In-memory storage for active WebSocket connections
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        # Track user info for active sessions
        self._session_users: Dict[str, Dict[str, UserInfo]] = {}

    async def create_session(
        self, design_id: UUID, user_id: str, username: str
    ) -> CollaborationSession:
        """
        Create or join a collaboration session for a design.

        Args:
            design_id: The design document ID
            user_id: The user joining the session
            username: The username for display

        Returns:
            CollaborationSession: The created or existing session

        Raises:
            NotFoundError: If the design doesn't exist
        """
        async with AsyncSessionLocal() as session:
            # Check if design exists
            design_repo = BaseRepository(Design, session)
            design = await design_repo.get(str(design_id))
            if not design:
                raise NotFoundError(f"Design with ID {design_id} not found")

            # Check for existing active session
            collab_repo = BaseRepository(CollaborationSession, session)
            existing_sessions = await session.execute(
                select(CollaborationSession).where(
                    CollaborationSession.design_id == str(design_id),
                    CollaborationSession.is_active == True,
                )
            )
            existing_session = existing_sessions.scalar_one_or_none()

            if existing_session:
                # Add user to existing session
                active_users = existing_session.active_users or []
                user_info = {"user_id": user_id, "username": username}

                # Check if user is already in session
                if not any(u.get("user_id") == user_id for u in active_users):
                    active_users.append(user_info)
                    existing_session.active_users = active_users
                    await session.commit()

                # Initialize session users tracking
                session_id = existing_session.id
                if session_id not in self._session_users:
                    self._session_users[session_id] = {}
                self._session_users[session_id][user_id] = UserInfo(user_id, username)

                return existing_session

            # Create new session
            session_data = {
                "design_id": str(design_id),
                "active_users": [{"user_id": user_id, "username": username}],
                "is_active": True,
                "created_at": datetime.utcnow(),
            }

            new_session = await collab_repo.create(**session_data)
            await session.commit()

            # Initialize session users tracking
            session_id = new_session.id
            self._session_users[session_id] = {user_id: UserInfo(user_id, username)}

            logger.info(
                f"Created collaboration session {session_id} for design {design_id}"
            )
            return new_session

    async def add_connection(self, session_id: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection to a session."""
        if session_id not in self._active_connections:
            self._active_connections[session_id] = set()
        self._active_connections[session_id].add(websocket)
        logger.info(f"Added WebSocket connection to session {session_id}")

    async def remove_connection(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from a session."""
        if session_id in self._active_connections:
            self._active_connections[session_id].discard(websocket)
            if not self._active_connections[session_id]:
                del self._active_connections[session_id]
        logger.info(f"Removed WebSocket connection from session {session_id}")

    async def broadcast_change(
        self,
        session_id: str,
        change: DesignChange,
        exclude_websocket: Optional[WebSocket] = None,
    ) -> None:
        """
        Broadcast a design change to all participants in a session.

        Args:
            session_id: The collaboration session ID
            change: The design change to broadcast
            exclude_websocket: WebSocket to exclude from broadcast (sender)
        """
        if session_id not in self._active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return

        message = {"type": "design_change", "data": change.to_dict()}

        # Broadcast to all connections except the sender
        connections_to_remove = []
        for websocket in self._active_connections[session_id]:
            if websocket == exclude_websocket:
                continue

            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")
                connections_to_remove.append(websocket)

        # Remove failed connections
        for websocket in connections_to_remove:
            await self.remove_connection(session_id, websocket)

        logger.info(
            f"Broadcasted change to {len(self._active_connections.get(session_id, []))} connections"
        )

    async def resolve_conflict(
        self, session_id: str, conflicts: List[DesignConflict]
    ) -> Design:
        """
        Resolve concurrent edit conflicts using last-write-wins strategy.

        Args:
            session_id: The collaboration session ID
            conflicts: List of conflicts to resolve

        Returns:
            Design: The updated design with conflicts resolved

        Raises:
            NotFoundError: If session or design not found
        """
        async with AsyncSessionLocal() as session:
            # Get the collaboration session
            collab_repo = BaseRepository(CollaborationSession, session)
            collab_session = await collab_repo.get(session_id)
            if not collab_session:
                raise NotFoundError(f"Collaboration session {session_id} not found")

            # Get the design
            design_repo = BaseRepository(Design, session)
            design = await design_repo.get(collab_session.design_id)
            if not design:
                raise NotFoundError(f"Design {collab_session.design_id} not found")

            # Apply last-write-wins resolution
            resolved_changes = {}
            for conflict in conflicts:
                # Sort changes by timestamp (latest first)
                sorted_changes = sorted(
                    conflict.changes, key=lambda c: c.timestamp, reverse=True
                )

                # Take the latest change (last-write-wins)
                if sorted_changes:
                    latest_change = sorted_changes[0]
                    resolved_changes[conflict.element_id] = latest_change.data

                    logger.info(
                        f"Resolved conflict for element {conflict.element_id} "
                        f"using change from user {latest_change.user_id}"
                    )

            # Update design with resolved changes
            if resolved_changes:
                # Increment version for conflict resolution
                design.version_number += 1
                design.current_version = f"{design.version_number}.0"
                design.updated_at = datetime.utcnow()

                await session.commit()

                # Broadcast resolution to all participants
                resolution_change = DesignChange(
                    change_type="conflict_resolution",
                    element_id="design",
                    data={"resolved_elements": list(resolved_changes.keys())},
                    user_id="system",
                )
                await self.broadcast_change(session_id, resolution_change)

            return design

    async def handle_disconnect(
        self, session_id: str, user_id: str, websocket: WebSocket
    ) -> None:
        """
        Handle user disconnection from a collaboration session.

        Args:
            session_id: The collaboration session ID
            user_id: The disconnecting user ID
            websocket: The WebSocket connection being closed
        """
        # Remove WebSocket connection
        await self.remove_connection(session_id, websocket)

        # Remove user from session tracking
        if session_id in self._session_users:
            self._session_users[session_id].pop(user_id, None)

        async with AsyncSessionLocal() as session:
            # Update database session
            collab_repo = BaseRepository(CollaborationSession, session)
            collab_session = await collab_repo.get(session_id)
            if collab_session:
                active_users = collab_session.active_users or []
                # Remove user from active users list
                active_users = [
                    user for user in active_users if user.get("user_id") != user_id
                ]
                collab_session.active_users = active_users

                # End session if no users left
                if not active_users:
                    collab_session.is_active = False
                    collab_session.ended_at = datetime.utcnow()
                    # Clean up session tracking
                    self._session_users.pop(session_id, None)
                    logger.info(
                        f"Ended collaboration session {session_id} - no users remaining"
                    )

                await session.commit()

        # Notify remaining users about disconnection
        disconnect_change = DesignChange(
            change_type="user_disconnect",
            element_id="session",
            data={"user_id": user_id},
            user_id="system",
        )
        await self.broadcast_change(session_id, disconnect_change)

        logger.info(f"User {user_id} disconnected from session {session_id}")

    async def get_session_users(self, session_id: str) -> List[UserInfo]:
        """Get list of active users in a session."""
        if session_id not in self._session_users:
            return []
        return list(self._session_users[session_id].values())

    async def update_user_cursor(
        self, session_id: str, user_id: str, cursor_position: Dict[str, Any]
    ) -> None:
        """Update user cursor position and broadcast to other users."""
        if (
            session_id in self._session_users
            and user_id in self._session_users[session_id]
        ):
            self._session_users[session_id][user_id].cursor_position = cursor_position

            # Broadcast cursor update
            cursor_change = DesignChange(
                change_type="cursor_move",
                element_id="cursor",
                data={"user_id": user_id, "position": cursor_position},
                user_id=user_id,
            )
            await self.broadcast_change(session_id, cursor_change)
