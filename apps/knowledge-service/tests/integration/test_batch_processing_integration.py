"""Integration tests for enhanced batch processing functionality."""

import asyncio
import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from knowledge_service.services.batch_processing import (
    BatchFileResult, BatchJobPriority, BatchJobStatus, BatchProcessingResult,
    BatchProcessingService)


class TestBatchProcessingIntegration:
    """Integration tests for batch processing service."""

    def test_batch_service_initialization(self):
        """Test that batch service initializes correctly."""
        service = BatchProcessingService()

        assert service.max_concurrent > 0
        assert service.max_batch_size > 0
        assert service.processing_timeout > 0
        assert isinstance(service._active_jobs, dict)
        assert isinstance(service._job_queues, dict)
        assert len(service._job_queues) == 4  # Four priority levels

    @pytest.mark.asyncio
    async def test_create_batch_job_basic(self):
        """Test basic batch job creation."""
        service = BatchProcessingService()

        # Create mock files
        mock_files = []
        for i in range(3):
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"test_file_{i}.pdf"
            mock_file.read = AsyncMock(return_value=b"mock pdf content")
            mock_files.append(mock_file)

        # Create batch job
        job_id = await service.create_batch_job(
            files=mock_files,
            titles=["Title 1", "Title 2", "Title 3"],
            descriptions=["Desc 1", "Desc 2", "Desc 3"],
            priority=BatchJobPriority.NORMAL,
            process_immediately=False,  # Queue it instead
        )

        assert job_id is not None
        assert len(job_id) > 0
        assert job_id in service._active_jobs

        progress = service.get_job_progress(job_id)
        assert progress is not None
        assert progress.status == BatchJobStatus.QUEUED
        assert progress.total_files == 3
        assert progress.processed_files == 0

    @pytest.mark.asyncio
    async def test_job_progress_tracking_workflow(self):
        """Test complete job progress tracking workflow."""
        service = BatchProcessingService()

        # Create a job manually for testing
        job_id = "test-progress-job"
        from knowledge_service.services.batch_processing import \
            BatchJobProgress

        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PENDING,
            total_files=5,
            processed_files=0,
            successful_files=0,
            failed_files=0,
        )
        service._active_jobs[job_id] = progress

        # Simulate processing workflow
        service._update_job_progress(job_id, status=BatchJobStatus.PROCESSING)
        assert service.get_job_progress(job_id).status == BatchJobStatus.PROCESSING

        # Simulate file processing
        for i in range(5):
            service._update_job_progress(
                job_id,
                processed_files=i + 1,
                successful_files=i + 1,
                current_file=f"file_{i}.pdf",
            )

            current_progress = service.get_job_progress(job_id)
            assert current_progress.processed_files == i + 1
            assert current_progress.successful_files == i + 1
            assert current_progress.progress_percentage == ((i + 1) / 5) * 100

        # Complete the job
        service._update_job_progress(
            job_id, status=BatchJobStatus.COMPLETED, current_file=None
        )

        final_progress = service.get_job_progress(job_id)
        assert final_progress.status == BatchJobStatus.COMPLETED
        assert final_progress.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_job_cancellation_workflow(self):
        """Test job cancellation workflow."""
        service = BatchProcessingService()

        # Create a processing job
        job_id = "cancel-workflow-test"
        from knowledge_service.services.batch_processing import \
            BatchJobProgress

        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PROCESSING,
            total_files=10,
            processed_files=3,
            successful_files=2,
            failed_files=1,
        )
        service._active_jobs[job_id] = progress

        # Cancel the job
        success = await service.cancel_job(job_id)

        assert success is True
        cancelled_progress = service.get_job_progress(job_id)
        assert cancelled_progress.status == BatchJobStatus.CANCELLED

        # Try to cancel again (should fail)
        success = await service.cancel_job(job_id)
        assert success is False

    def test_priority_queue_ordering(self):
        """Test that priority queues maintain correct ordering."""
        service = BatchProcessingService()

        # Add jobs to different priority queues
        jobs = {
            "urgent": ["urgent-1", "urgent-2"],
            "high": ["high-1", "high-2", "high-3"],
            "normal": ["normal-1"],
            "low": ["low-1", "low-2"],
        }

        for priority_name, job_list in jobs.items():
            priority_value = BatchJobPriority[priority_name.upper()].value
            service._job_queues[priority_value].extend(job_list)

        # Verify queue contents
        assert len(service._job_queues[BatchJobPriority.URGENT.value]) == 2
        assert len(service._job_queues[BatchJobPriority.HIGH.value]) == 3
        assert len(service._job_queues[BatchJobPriority.NORMAL.value]) == 1
        assert len(service._job_queues[BatchJobPriority.LOW.value]) == 2

        # Test stats reflect correct counts
        stats = service.get_processing_stats()
        queue_stats = stats["current_status"]["queued_jobs_by_priority"]

        assert queue_stats["urgent"] == 2
        assert queue_stats["high"] == 3
        assert queue_stats["normal"] == 1
        assert queue_stats["low"] == 2
        assert stats["current_status"]["total_queued_jobs"] == 8

    def test_processing_stats_comprehensive(self):
        """Test comprehensive processing statistics."""
        service = BatchProcessingService()

        # Add various jobs to simulate real usage
        from knowledge_service.services.batch_processing import \
            BatchJobProgress

        # Active jobs
        service._active_jobs["processing-1"] = BatchJobProgress(
            job_id="processing-1",
            status=BatchJobStatus.PROCESSING,
            total_files=10,
            processed_files=5,
            successful_files=4,
            failed_files=1,
        )

        service._active_jobs["completed-1"] = BatchJobProgress(
            job_id="completed-1",
            status=BatchJobStatus.COMPLETED,
            total_files=5,
            processed_files=5,
            successful_files=5,
            failed_files=0,
        )

        service._active_jobs["failed-1"] = BatchJobProgress(
            job_id="failed-1",
            status=BatchJobStatus.FAILED,
            total_files=3,
            processed_files=3,
            successful_files=1,
            failed_files=2,
        )

        # Queued jobs
        service._job_queues[BatchJobPriority.HIGH.value].extend(
            ["queued-1", "queued-2"]
        )
        service._job_queues[BatchJobPriority.NORMAL.value].append("queued-3")

        stats = service.get_processing_stats()

        # Verify system config
        assert "system_config" in stats
        system_config = stats["system_config"]
        assert "max_concurrent_processing" in system_config
        assert "max_batch_size" in system_config
        assert "processing_timeout_minutes" in system_config
        assert "supported_file_types" in system_config
        assert "max_file_size_mb" in system_config

        # Verify current status
        assert "current_status" in stats
        current_status = stats["current_status"]
        assert current_status["active_jobs_count"] == 3
        assert current_status["total_queued_jobs"] == 3

        # Verify job status breakdown
        status_breakdown = current_status["active_jobs_by_status"]
        assert status_breakdown.get("processing", 0) == 1
        assert status_breakdown.get("completed", 0) == 1
        assert status_breakdown.get("failed", 0) == 1

        # Verify capabilities
        assert "capabilities" in stats
        capabilities = stats["capabilities"]
        assert capabilities["progress_tracking"] is True
        assert capabilities["job_queuing"] is True
        assert capabilities["job_retry"] is True
        assert capabilities["job_cancellation"] is True
        assert capabilities["priority_processing"] is True
        assert capabilities["progress_callbacks"] is True

    @pytest.mark.asyncio
    async def test_batch_processing_error_handling(self):
        """Test error handling in batch processing."""
        service = BatchProcessingService()

        # Test with empty file list
        with pytest.raises(Exception):  # Should raise validation error
            await service.create_batch_job(files=[])

        # Test with mismatched titles
        mock_files = [Mock(spec=UploadFile) for _ in range(2)]
        for i, file in enumerate(mock_files):
            file.filename = f"test_{i}.pdf"

        with pytest.raises(Exception):  # Should raise validation error
            await service.create_batch_job(
                files=mock_files, titles=["Title 1"]  # Only one title for two files
            )

        # Test with too many files
        too_many_files = [
            Mock(spec=UploadFile) for _ in range(service.max_batch_size + 1)
        ]
        for i, file in enumerate(too_many_files):
            file.filename = f"test_{i}.pdf"

        with pytest.raises(Exception):  # Should raise batch size error
            await service.create_batch_job(files=too_many_files)

    def test_callback_system(self):
        """Test progress callback system."""
        service = BatchProcessingService()

        callback_calls = []

        def test_callback(progress):
            callback_calls.append(
                {
                    "job_id": progress.job_id,
                    "status": progress.status,
                    "progress": progress.progress_percentage,
                }
            )

        job_id = "callback-test"
        service.register_progress_callback(job_id, test_callback)

        # Create and update job progress
        from knowledge_service.services.batch_processing import \
            BatchJobProgress

        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PROCESSING,
            total_files=4,
            processed_files=0,
            successful_files=0,
            failed_files=0,
        )
        service._active_jobs[job_id] = progress

        # Simulate progress updates
        service._update_job_progress(job_id, processed_files=1, successful_files=1)
        service._update_job_progress(job_id, processed_files=2, successful_files=2)
        service._update_job_progress(
            job_id,
            processed_files=4,
            successful_files=3,
            failed_files=1,
            status=BatchJobStatus.PARTIAL_SUCCESS,
        )

        # Verify callbacks were called
        assert len(callback_calls) == 3
        assert callback_calls[0]["progress"] == 25.0  # 1/4
        assert callback_calls[1]["progress"] == 50.0  # 2/4
        assert callback_calls[2]["progress"] == 100.0  # 4/4
        assert callback_calls[2]["status"] == BatchJobStatus.PARTIAL_SUCCESS

    def test_job_cleanup_logic(self):
        """Test job cleanup logic."""
        service = BatchProcessingService()

        # Add completed and active jobs
        from knowledge_service.services.batch_processing import \
            BatchJobProgress

        service._active_jobs["completed-old"] = BatchJobProgress(
            job_id="completed-old",
            status=BatchJobStatus.COMPLETED,
            total_files=5,
            processed_files=5,
            successful_files=5,
            failed_files=0,
        )

        service._active_jobs["failed-old"] = BatchJobProgress(
            job_id="failed-old",
            status=BatchJobStatus.FAILED,
            total_files=3,
            processed_files=3,
            successful_files=1,
            failed_files=2,
        )

        service._active_jobs["processing-current"] = BatchJobProgress(
            job_id="processing-current",
            status=BatchJobStatus.PROCESSING,
            total_files=10,
            processed_files=5,
            successful_files=4,
            failed_files=1,
        )

        # Add callbacks for completed jobs
        service._progress_callbacks["completed-old"] = Mock()
        service._progress_callbacks["failed-old"] = Mock()
        service._progress_callbacks["processing-current"] = Mock()

        # Cleanup (without database)
        service.cleanup_completed_jobs(older_than_hours=24, db=None)

        # Verify cleanup
        assert "completed-old" not in service._active_jobs
        assert "failed-old" not in service._active_jobs
        assert "processing-current" in service._active_jobs  # Should remain

        assert "completed-old" not in service._progress_callbacks
        assert "failed-old" not in service._progress_callbacks
        assert "processing-current" in service._progress_callbacks  # Should remain
