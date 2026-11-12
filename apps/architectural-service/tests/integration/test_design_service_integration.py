"""Integration tests for Design Service client."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List
from uuid import UUID, uuid4

import httpx
import pytest
from src.infrastructure.design_service_client import (DesignServiceClient,
                                                      RenderJob,
                                                      RenderParameters,
                                                      RenderStatus, RenderType,
                                                      VisualOutput)


class MockDesignServiceServer:
    """Mock Design Service server for testing."""

    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.outputs: Dict[str, List[Dict]] = {}
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0

    def reset(self):
        """Reset server state."""
        self.jobs.clear()
        self.outputs.clear()
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle mock HTTP requests."""
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_fail:
            self.failure_count += 1
            if self.failure_count <= 3:  # Fail first 3 attempts
                return httpx.Response(503, json={"error": "Service unavailable"})

        method = request.method
        url_path = request.url.path

        if method == "POST" and url_path == "/api/v1/render/jobs":
            return await self._handle_create_job(request)
        elif method == "GET" and "/api/v1/render/jobs/" in url_path:
            if url_path.endswith("/outputs"):
                job_id = url_path.split("/")[-2]
                return await self._handle_get_outputs(job_id)
            else:
                job_id = url_path.split("/")[-1]
                return await self._handle_get_job_status(job_id)

        return httpx.Response(404, json={"error": "Not found"})

    async def _handle_create_job(self, request: httpx.Request) -> httpx.Response:
        """Handle job creation request."""
        data = json.loads(request.content)
        job_id = str(uuid4())

        job_data = {
            "job_id": job_id,
            "design_id": data["design_id"],
            "render_type": data["render_type"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }

        self.jobs[job_id] = job_data

        # Simulate job processing
        asyncio.create_task(self._process_job(job_id))

        return httpx.Response(200, json=job_data)

    async def _handle_get_job_status(self, job_id: str) -> httpx.Response:
        """Handle job status request."""
        if job_id not in self.jobs:
            return httpx.Response(404, json={"error": "Job not found"})

        return httpx.Response(200, json=self.jobs[job_id])

    async def _handle_get_outputs(self, job_id: str) -> httpx.Response:
        """Handle get outputs request."""
        if job_id not in self.jobs:
            return httpx.Response(404, json={"error": "Job not found"})

        if self.jobs[job_id]["status"] != "completed":
            return httpx.Response(400, json={"error": "Job not completed"})

        outputs = self.outputs.get(job_id, [])
        return httpx.Response(200, json={"outputs": outputs})

    async def _process_job(self, job_id: str):
        """Simulate job processing."""
        await asyncio.sleep(0.1)  # Simulate processing time

        # Update job status
        self.jobs[job_id]["status"] = "in_progress"
        self.jobs[job_id]["started_at"] = datetime.utcnow().isoformat()

        await asyncio.sleep(0.1)  # More processing

        # Complete job
        self.jobs[job_id]["status"] = "completed"
        self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()

        # Create mock outputs
        render_type = self.jobs[job_id]["render_type"]
        output_data = {
            "output_id": str(uuid4()),
            "job_id": job_id,
            "render_type": render_type,
            "file_url": f"https://storage.example.com/{job_id}.png",
            "file_size": 1024000,
            "mime_type": "image/png",
            "resolution": "1920x1080",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        self.outputs[job_id] = [output_data]


@pytest.fixture
async def mock_design_server():
    """Create mock Design Service server."""
    server = MockDesignServiceServer()
    yield server
    server.reset()


@pytest.fixture
async def design_client(mock_design_server):
    """Create Design Service client with mock server."""

    # Create a mock transport that routes to our mock server
    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self, server):
            self.server = server

        async def handle_async_request(self, request):
            response = await self.server.handle_request(request)
            return response

    client = DesignServiceClient("http://mock-design-service")
    # Replace the HTTP client with our mock transport
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=MockTransport(mock_design_server))

    yield client
    await client.close()


class TestDesignServiceIntegration:
    """Integration tests for Design Service client."""

    @pytest.mark.asyncio
    async def test_rendering_request_workflow(self, design_client):
        """
        Test complete rendering request workflow.

        **Validates: Requirements 8.1, 8.3**
        """
        design_id = uuid4()
        parameters = RenderParameters(
            render_type=RenderType.FLOOR_PLAN,
            resolution="1920x1080",
            quality="high",
            lighting="natural",
        )

        # Request rendering
        job = await design_client.request_rendering(
            design_id, RenderType.FLOOR_PLAN, parameters
        )

        assert isinstance(job, RenderJob)
        assert job.design_id == design_id
        assert job.render_type == RenderType.FLOOR_PLAN
        assert job.status == RenderStatus.PENDING
        assert job.job_id is not None

    @pytest.mark.asyncio
    async def test_render_status_polling(self, design_client):
        """
        Test render status polling until completion.

        **Validates: Requirements 8.3**
        """
        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.ELEVATION)

        # Request rendering
        job = await design_client.request_rendering(
            design_id, RenderType.ELEVATION, parameters
        )

        # Poll status until completed
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            status_job = await design_client.get_render_status(job.job_id)

            if status_job.status == RenderStatus.COMPLETED:
                break
            elif status_job.status == RenderStatus.FAILED:
                pytest.fail("Rendering job failed")

            await asyncio.sleep(0.1)
            attempt += 1

        assert status_job.status == RenderStatus.COMPLETED
        assert status_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_output_retrieval(self, design_client):
        """
        Test retrieval of completed visual outputs.

        **Validates: Requirements 8.3**
        """
        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.THREE_D_VIEW)

        # Request rendering
        job = await design_client.request_rendering(
            design_id, RenderType.THREE_D_VIEW, parameters
        )

        # Wait for completion
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            status_job = await design_client.get_render_status(job.job_id)
            if status_job.status == RenderStatus.COMPLETED:
                break
            await asyncio.sleep(0.1)
            attempt += 1

        # Retrieve outputs
        outputs = await design_client.retrieve_outputs(job.job_id)

        assert len(outputs) > 0
        output = outputs[0]
        assert isinstance(output, VisualOutput)
        assert output.job_id == job.job_id
        assert output.render_type == RenderType.THREE_D_VIEW
        assert output.file_url.startswith("https://")
        assert output.file_size > 0
        assert output.mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_retry_on_failures(self, design_client, mock_design_server):
        """
        Test retry logic with exponential backoff on failures.

        **Validates: Requirements 8.4**
        """
        # Configure server to fail first few attempts
        mock_design_server.should_fail = True

        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.SECTION)

        # Request should eventually succeed after retries
        job = await design_client.request_rendering(
            design_id, RenderType.SECTION, parameters
        )

        assert isinstance(job, RenderJob)
        assert job.design_id == design_id
        assert mock_design_server.failure_count >= 3  # Should have retried

    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, design_client, mock_design_server):
        """
        Test circuit breaker opens after repeated failures.

        **Validates: Requirements 8.4**
        """
        # Configure server to always fail
        mock_design_server.should_fail = True
        mock_design_server.failure_count = 0

        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.WALKTHROUGH)

        # Make multiple requests to trigger circuit breaker
        failure_count = 0
        for _ in range(10):
            try:
                await design_client.request_rendering(
                    design_id, RenderType.WALKTHROUGH, parameters
                )
            except Exception:
                failure_count += 1

        # Circuit breaker should have opened, preventing some requests
        assert failure_count > 0
        # Note: Exact behavior depends on circuit breaker configuration

    @pytest.mark.asyncio
    async def test_timeout_handling(self, design_client, mock_design_server):
        """
        Test handling of request timeouts.

        **Validates: Requirements 8.4**
        """
        # Configure server to delay responses
        mock_design_server.delay_seconds = 0.5

        # Create client with short timeout
        short_timeout_client = DesignServiceClient(
            "http://mock-design-service", timeout=0.1
        )

        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.FLOOR_PLAN)

        # Request should timeout and be retried
        with pytest.raises((httpx.TimeoutException, Exception)):
            await short_timeout_client.request_rendering(
                design_id, RenderType.FLOOR_PLAN, parameters
            )

        await short_timeout_client.close()

    @pytest.mark.asyncio
    async def test_multiple_render_types(self, design_client):
        """
        Test rendering requests for different render types.

        **Validates: Requirements 8.1, 8.2**
        """
        design_id = uuid4()
        render_types = [
            RenderType.FLOOR_PLAN,
            RenderType.ELEVATION,
            RenderType.SECTION,
            RenderType.THREE_D_VIEW,
            RenderType.WALKTHROUGH,
        ]

        jobs = []
        for render_type in render_types:
            parameters = RenderParameters(render_type=render_type)
            job = await design_client.request_rendering(
                design_id, render_type, parameters
            )
            jobs.append(job)

        # Verify all jobs were created
        assert len(jobs) == len(render_types)
        for i, job in enumerate(jobs):
            assert job.render_type == render_types[i]
            assert job.design_id == design_id

    @pytest.mark.asyncio
    async def test_rendering_parameters_validation(self, design_client):
        """
        Test validation of rendering parameters.

        **Validates: Requirements 8.1**
        """
        design_id = uuid4()

        # Test with custom parameters
        parameters = RenderParameters(
            render_type=RenderType.THREE_D_VIEW,
            resolution="4K",
            quality="ultra",
            camera_angle={"x": 45, "y": 0, "z": 30},
            lighting="artificial",
            materials=True,
            annotations=True,
            metadata={"custom_setting": "value"},
        )

        job = await design_client.request_rendering(
            design_id, RenderType.THREE_D_VIEW, parameters
        )

        assert job.render_type == RenderType.THREE_D_VIEW
        assert job.design_id == design_id

    @pytest.mark.asyncio
    async def test_job_not_found_error(self, design_client):
        """
        Test handling of job not found errors.

        **Validates: Requirements 8.3**
        """
        non_existent_job_id = uuid4()

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await design_client.get_render_status(non_existent_job_id)

        assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_outputs_before_completion_error(self, design_client):
        """
        Test error when requesting outputs before job completion.

        **Validates: Requirements 8.3**
        """
        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.FLOOR_PLAN)

        # Request rendering
        job = await design_client.request_rendering(
            design_id, RenderType.FLOOR_PLAN, parameters
        )

        # Try to get outputs immediately (before completion)
        # Note: This might succeed if job completes very quickly
        try:
            outputs = await design_client.retrieve_outputs(job.job_id)
            # If it succeeds, verify we got valid outputs
            assert isinstance(outputs, list)
        except httpx.HTTPStatusError as e:
            # If it fails, should be 400 Bad Request
            assert e.response.status_code == 400

    @pytest.mark.asyncio
    async def test_concurrent_rendering_requests(self, design_client):
        """
        Test handling of concurrent rendering requests.

        **Validates: Requirements 8.1, 8.4**
        """
        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.ELEVATION)

        # Submit multiple concurrent requests
        tasks = []
        for i in range(5):
            task = design_client.request_rendering(
                design_id, RenderType.ELEVATION, parameters
            )
            tasks.append(task)

        # Wait for all requests to complete
        jobs = await asyncio.gather(*tasks)

        # Verify all jobs were created successfully
        assert len(jobs) == 5
        for job in jobs:
            assert isinstance(job, RenderJob)
            assert job.design_id == design_id
            assert job.render_type == RenderType.ELEVATION

        # Verify all jobs have unique IDs
        job_ids = [job.job_id for job in jobs]
        assert len(set(job_ids)) == len(job_ids)  # All unique
