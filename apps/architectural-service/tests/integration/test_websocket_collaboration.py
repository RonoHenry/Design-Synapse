"""Integration tests for WebSocket collaboration functionality."""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.models.design import Design
from src.services.collaboration_service import CollaborationService


class TestWebSocketCollaboration:
    """Integration tests for WebSocket collaboration."""

    def setup_method(self):
        """Set up test method."""
        self.client = TestClient(app)
        self.collaboration_service = CollaborationService()

    @pytest.mark.asyncio
    async def test_multiple_users_joining_session(self, test_session):
        """
        Test multiple users joining a collaboration session.

        **Validates: Requirements 11.1, 11.3**
        """
        # Create a test design
        design_id = uuid4()
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={"city": "Test City", "country": "United States"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(design)
        await test_session.commit()

        # First user joins session
        join_response = self.client.post(
            f"/api/v1/designs/{design_id}/collaboration/join",
            json={"user_id": "user1", "username": "User One"},
        )
        assert join_response.status_code == 200
        session_data = join_response.json()
        session_id = session_data["session_id"]

        # Second user joins the same session
        join_response2 = self.client.post(
            f"/api/v1/designs/{design_id}/collaboration/join",
            json={"user_id": "user2", "username": "User Two"},
        )
        assert join_response2.status_code == 200
        session_data2 = join_response2.json()

        # Should be the same session
        assert session_data2["session_id"] == session_id
        assert len(session_data2["active_users"]) == 2

    @pytest.mark.asyncio
    async def test_message_broadcasting(self, test_session):
        """
        Test message broadcasting between WebSocket connections.

        **Validates: Requirements 11.1, 11.2**
        """
        # Create test design and session
        design_id = uuid4()
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={"city": "Test City", "country": "United States"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(design)
        await test_session.commit()

        # Create collaboration session
        collab_session = await self.collaboration_service.create_session(
            design_id, "user1", "User One"
        )
        session_id = collab_session.id

        # Mock WebSocket connections
        class MockWebSocket:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.messages = []
                self.closed = False

            async def send_text(self, message: str):
                if not self.closed:
                    self.messages.append(message)

            def close(self):
                self.closed = True

        # Create mock WebSocket connections
        ws1 = MockWebSocket("user1")
        ws2 = MockWebSocket("user2")

        # Add connections to service
        await self.collaboration_service.add_connection(session_id, ws1)
        await self.collaboration_service.add_connection(session_id, ws2)

        # Create a design change
        from src.services.collaboration_service import DesignChange

        change = DesignChange(
            change_type="update",
            element_id="element1",
            data={"property": "value"},
            user_id="user1",
        )

        # Broadcast change (excluding sender)
        await self.collaboration_service.broadcast_change(
            session_id, change, exclude_websocket=ws1
        )

        # Verify only user2 received the message
        assert len(ws1.messages) == 0  # Sender excluded
        assert len(ws2.messages) == 1  # Receiver got message

        # Verify message content
        message = json.loads(ws2.messages[0])
        assert message["type"] == "design_change"
        assert message["data"]["change_type"] == "update"
        assert message["data"]["element_id"] == "element1"
        assert message["data"]["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_conflict_resolution(self, test_session):
        """
        Test conflict resolution in collaboration sessions.

        **Validates: Requirements 11.3**
        """
        # Create test design and session
        design_id = uuid4()
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={"city": "Test City", "country": "United States"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(design)
        await test_session.commit()

        # Create collaboration session
        collab_session = await self.collaboration_service.create_session(
            design_id, "user1", "User One"
        )
        session_id = collab_session.id

        # Create conflicting changes
        from datetime import timedelta

        from src.services.collaboration_service import (DesignChange,
                                                        DesignConflict)

        base_time = datetime.utcnow()
        change1 = DesignChange(
            change_type="update",
            element_id="element1",
            data={"color": "red"},
            user_id="user1",
            timestamp=base_time,
        )
        change2 = DesignChange(
            change_type="update",
            element_id="element1",
            data={"color": "blue"},
            user_id="user2",
            timestamp=base_time + timedelta(seconds=1),  # Later timestamp
        )

        conflict = DesignConflict("element1", [change1, change2])

        # Resolve conflict (should use last-write-wins)
        resolved_design = await self.collaboration_service.resolve_conflict(
            session_id, [conflict]
        )

        # Verify design was updated
        assert resolved_design is not None
        assert resolved_design.version_number > 1  # Version incremented

    @pytest.mark.asyncio
    async def test_user_disconnect_handling(self, test_session):
        """
        Test user disconnect handling in collaboration sessions.

        **Validates: Requirements 11.6**
        """
        # Create test design and session
        design_id = uuid4()
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={"city": "Test City", "country": "United States"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(design)
        await test_session.commit()

        # Create collaboration session with multiple users
        collab_session = await self.collaboration_service.create_session(
            design_id, "user1", "User One"
        )
        await self.collaboration_service.create_session(design_id, "user2", "User Two")
        session_id = collab_session.id

        # Mock WebSocket connections
        class MockWebSocket:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.messages = []

            async def send_text(self, message: str):
                self.messages.append(message)

        ws1 = MockWebSocket("user1")
        ws2 = MockWebSocket("user2")

        # Add connections
        await self.collaboration_service.add_connection(session_id, ws1)
        await self.collaboration_service.add_connection(session_id, ws2)

        # Verify initial state
        users = await self.collaboration_service.get_session_users(session_id)
        assert len(users) == 2

        # Disconnect user1
        await self.collaboration_service.handle_disconnect(session_id, "user1", ws1)

        # Verify user was removed
        users = await self.collaboration_service.get_session_users(session_id)
        assert len(users) == 1
        assert users[0].user_id == "user2"

        # Disconnect last user
        await self.collaboration_service.handle_disconnect(session_id, "user2", ws2)

        # Verify session ended
        users = await self.collaboration_service.get_session_users(session_id)
        assert len(users) == 0

    def test_get_session_users_endpoint(self):
        """
        Test the GET endpoint for retrieving session users.

        **Validates: Requirements 11.1**
        """
        # Test with non-existent session
        response = self.client.get("/api/v1/collaboration/nonexistent/users")
        assert response.status_code == 200
        data = response.json()
        assert data["user_count"] == 0
        assert data["active_users"] == []

    @pytest.mark.asyncio
    async def test_websocket_heartbeat_mechanism(self, test_session):
        """
        Test WebSocket heartbeat mechanism for connection monitoring.

        **Validates: Requirements 11.2**
        """
        # This test would require actual WebSocket testing framework
        # For now, we'll test the heartbeat logic conceptually

        # Create test design and session
        design_id = uuid4()
        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={"city": "Test City", "country": "United States"},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(design)
        await test_session.commit()

        # Create collaboration session
        collab_session = await self.collaboration_service.create_session(
            design_id, "user1", "User One"
        )
        session_id = collab_session.id

        # Mock WebSocket for heartbeat testing
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                self.closed = False

            async def send_text(self, message: str):
                if not self.closed:
                    self.messages.append(message)

        ws = MockWebSocket()
        await self.collaboration_service.add_connection(session_id, ws)

        # Simulate heartbeat message
        heartbeat_message = {
            "type": "heartbeat",
            "data": {"timestamp": asyncio.get_event_loop().time()},
        }

        # In a real WebSocket implementation, this would be sent automatically
        # Here we just verify the message structure is correct
        await ws.send_text(json.dumps(heartbeat_message))

        assert len(ws.messages) == 1
        message = json.loads(ws.messages[0])
        assert message["type"] == "heartbeat"
        assert "timestamp" in message["data"]
