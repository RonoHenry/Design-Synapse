"""Tests for enhanced batch processing capabilities."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from knowledge_service.services.batch_processing import (
    BatchJob, BatchJobPriority, BatchJobProgress, BatchJobStatus,
    BatchProcessingResult, BatchProcessingService)


class TestEnhancedBatchProcessing:
    """Test enhanced batch processing capabilities."""

    @pytest.fixture
    def batch_service(self):
        """Create a batch processing service for testing."""
        return BatchProcessingService()

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        session.add = Mock()
        session.commit = Mock()
        return session

    def test_job_progress_tracking(self, batch_service):
        """Test job progress tracking functionality."""
        job_id = "test-job-123"

        # Create initial progress
        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PENDING,
            total_files=10,
            processed_files=0,
            successful_files=0,
            failed_files=0,
        )
        batch_service._active_jobs[job_id] = progress

        # Test progress updates
        batch_service._update_job_progress(
            job_id,
            status=BatchJobStatus.PROCESSING,
            processed_files=3,
            successful_files=2,
            failed_files=1,
            current_file="test.pdf",
        )

        updated_progress = batch_service.get_job_progress(job_id)
        assert updated_progress is not None
        assert updated_progress.status == BatchJobStatus.PROCESSING
        assert updated_progress.processed_files == 3
        assert updated_progress.successful_files == 2
        assert updated_progress.failed_files == 1
        assert updated_progress.current_file == "test.pdf"
        assert updated_progress.progress_percentage == 30.0  # 3/10 * 100

    def test_job_priority_queuing(self, batch_service):
        """Test job priority queuing system."""
        # Add jobs with different priorities
        urgent_job = "urgent-job"
        high_job = "high-job"
        normal_job = "normal-job"
        low_job = "low-job"

        batch_service._job_queues[BatchJobPriority.LOW.value].append(low_job)
        batch_service._job_queues[BatchJobPriority.NORMAL.value].append(normal_job)
        batch_service._job_queues[BatchJobPriority.HIGH.value].append(high_job)
        batch_service._job_queues[BatchJobPriority.URGENT.value].append(urgent_job)

        # Verify queue contents
        assert urgent_job in batch_service._job_queues[BatchJobPriority.URGENT.value]
        assert high_job in batch_service._job_queues[BatchJobPriority.HIGH.value]
        assert normal_job in batch_service._job_queues[BatchJobPriority.NORMAL.value]
        assert low_job in batch_service._job_queues[BatchJobPriority.LOW.value]

    @pytest.mark.asyncio
    async def test_job_cancellation(self, batch_service, mock_db_session):
        """Test job cancellation functionality."""
        job_id = "cancel-test-job"

        # Create a processing job
        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PROCESSING,
            total_files=5,
            processed_files=2,
            successful_files=1,
            failed_files=1,
        )
        batch_service._active_jobs[job_id] = progress

        # Mock database job
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = BatchJobStatus.PROCESSING.value
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_job
        )

        # Cancel the job
        success = await batch_service.cancel_job(job_id, mock_db_session)

        assert success is True
        assert batch_service.get_job_progress(job_id).status == BatchJobStatus.CANCELLED
        assert mock_job.status == BatchJobStatus.CANCELLED.value
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_job_retry_functionality(self, batch_service, mock_db_session):
        """Test job retry functionality."""
        job_id = "retry-test-job"

        # Mock a failed job in database
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = BatchJobStatus.FAILED.value
        mock_job.retry_count = 1
        mock_job.max_retries = 3
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_job
        )

        # Retry the job
        success = await batch_service.retry_job(job_id, mock_db_session)

        assert success is True
        assert mock_job.status == BatchJobStatus.RETRYING.value
        assert mock_job.retry_count == 2
        assert job_id in batch_service._job_queues[BatchJobPriority.HIGH.value]
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_job_retry_max_attempts_exceeded(
        self, batch_service, mock_db_session
    ):
        """Test job retry when max attempts exceeded."""
        job_id = "max-retry-test-job"

        # Mock a failed job that has exceeded max retries
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = BatchJobStatus.FAILED.value
        mock_job.retry_count = 3
        mock_job.max_retries = 3
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_job
        )

        # Try to retry the job
        success = await batch_service.retry_job(job_id, mock_db_session)

        assert success is False
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self, batch_service, mock_db_session):
        """Test job pause and resume functionality."""
        job_id = "pause-resume-test-job"

        # Create a processing job
        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PROCESSING,
            total_files=5,
            processed_files=2,
            successful_files=1,
            failed_files=1,
        )
        batch_service._active_jobs[job_id] = progress

        # Mock database job
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = BatchJobStatus.PROCESSING.value
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_job
        )

        # Pause the job
        success = await batch_service.pause_job(job_id, mock_db_session)
        assert success is True
        assert batch_service.get_job_progress(job_id).status == BatchJobStatus.PAUSED

        # Update mock for resume
        mock_job.status = BatchJobStatus.PAUSED.value

        # Resume the job
        success = await batch_service.resume_job(job_id, mock_db_session)
        assert success is True
        assert job_id in batch_service._job_queues[BatchJobPriority.HIGH.value]

    def test_progress_callback_registration(self, batch_service):
        """Test progress callback registration and notification."""
        job_id = "callback-test-job"
        callback_called = False
        callback_progress = None

        def test_callback(progress: BatchJobProgress):
            nonlocal callback_called, callback_progress
            callback_called = True
            callback_progress = progress

        # Register callback
        batch_service.register_progress_callback(job_id, test_callback)

        # Create progress and trigger update
        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PROCESSING,
            total_files=5,
            processed_files=1,
            successful_files=1,
            failed_files=0,
        )
        batch_service._active_jobs[job_id] = progress

        # Update progress (should trigger callback)
        batch_service._update_job_progress(job_id, processed_files=2)

        assert callback_called is True
        assert callback_progress is not None
        assert callback_progress.job_id == job_id
        assert callback_progress.processed_files == 2

    def test_processing_stats_enhanced(self, batch_service):
        """Test enhanced processing statistics."""
        # Add some jobs to different queues
        batch_service._job_queues[BatchJobPriority.URGENT.value].append("urgent-1")
        batch_service._job_queues[BatchJobPriority.HIGH.value].extend(
            ["high-1", "high-2"]
        )
        batch_service._job_queues[BatchJobPriority.NORMAL.value].append("normal-1")

        # Add some active jobs
        batch_service._active_jobs["active-1"] = BatchJobProgress(
            job_id="active-1",
            status=BatchJobStatus.PROCESSING,
            total_files=5,
            processed_files=2,
            successful_files=1,
            failed_files=1,
        )
        batch_service._active_jobs["active-2"] = BatchJobProgress(
            job_id="active-2",
            status=BatchJobStatus.COMPLETED,
            total_files=3,
            processed_files=3,
            successful_files=3,
            failed_files=0,
        )

        stats = batch_service.get_processing_stats()

        # Verify system config
        assert "system_config" in stats
        assert "max_concurrent_processing" in stats["system_config"]
        assert "max_batch_size" in stats["system_config"]

        # Verify current status
        assert "current_status" in stats
        assert stats["current_status"]["active_jobs_count"] == 2
        assert stats["current_status"]["queued_jobs_by_priority"]["urgent"] == 1
        assert stats["current_status"]["queued_jobs_by_priority"]["high"] == 2
        assert stats["current_status"]["queued_jobs_by_priority"]["normal"] == 1
        assert stats["current_status"]["queued_jobs_by_priority"]["low"] == 0
        assert stats["current_status"]["total_queued_jobs"] == 4

        # Verify capabilities
        assert "capabilities" in stats
        assert stats["capabilities"]["progress_tracking"] is True
        assert stats["capabilities"]["job_queuing"] is True
        assert stats["capabilities"]["job_retry"] is True
        assert stats["capabilities"]["job_cancellation"] is True

    def test_job_history_retrieval(self, batch_service, mock_db_session):
        """Test job history retrieval from database."""
        # Mock database jobs
        mock_jobs = []
        for i in range(3):
            job = Mock()
            job.id = f"job-{i}"
            job.status = BatchJobStatus.COMPLETED.value
            job.total_files = 5
            job.processed_files = 5
            job.successful_files = 4
            job.failed_files = 1
            job.created_at = datetime.utcnow() - timedelta(hours=i)
            job.started_at = datetime.utcnow() - timedelta(hours=i, minutes=30)
            job.completed_at = datetime.utcnow() - timedelta(hours=i, minutes=15)
            job.processing_time_seconds = 900.0  # 15 minutes
            job.priority = BatchJobPriority.NORMAL.value
            job.retry_count = 0
            job.max_retries = 3
            job.user_id = 1
            job.error_message = None
            job.metadata = '{"author": "test"}'
            mock_jobs.append(job)

        mock_db_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_jobs
        )

        history = batch_service.get_job_history(limit=10, db=mock_db_session)

        assert len(history) == 3
        assert all("job_id" in job for job in history)
        assert all("status" in job for job in history)
        assert all("metadata" in job for job in history)

        # Verify metadata parsing
        assert history[0]["metadata"]["author"] == "test"

    def test_cleanup_completed_jobs(self, batch_service, mock_db_session):
        """Test cleanup of completed jobs."""
        # Mock database query for cleanup
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = 5
        mock_db_session.query.return_value = mock_query

        # Add some completed jobs to in-memory tracking
        batch_service._active_jobs["completed-1"] = BatchJobProgress(
            job_id="completed-1",
            status=BatchJobStatus.COMPLETED,
            total_files=3,
            processed_files=3,
            successful_files=3,
            failed_files=0,
        )
        batch_service._active_jobs["processing-1"] = BatchJobProgress(
            job_id="processing-1",
            status=BatchJobStatus.PROCESSING,
            total_files=5,
            processed_files=2,
            successful_files=1,
            failed_files=1,
        )

        # Add progress callback for completed job
        batch_service._progress_callbacks["completed-1"] = Mock()

        # Cleanup
        batch_service.cleanup_completed_jobs(older_than_hours=24, db=mock_db_session)

        # Verify database cleanup was called
        mock_db_session.commit.assert_called_once()

        # Verify in-memory cleanup
        assert "completed-1" not in batch_service._active_jobs
        assert "processing-1" in batch_service._active_jobs  # Should remain
        assert "completed-1" not in batch_service._progress_callbacks

    @pytest.mark.asyncio
    async def test_queue_processor_lifecycle(self, batch_service):
        """Test queue processor start and stop."""
        # Start queue processor
        await batch_service.start_queue_processor()
        assert batch_service._queue_processor_task is not None
        assert not batch_service._queue_processor_task.done()

        # Stop queue processor
        await batch_service.stop_queue_processor()
        assert batch_service._shutdown_event.is_set()
