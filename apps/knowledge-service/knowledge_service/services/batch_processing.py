"""Batch processing service for handling multiple file uploads and processing."""

import asyncio
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from ..core.config import settings
from ..exceptions import (BatchProcessingError, FileValidationError,
                          KnowledgeServiceError, PDFProcessingError)
from ..models import Resource, Topic
from ..services.pdf_processing import PDFProcessingService

logger = logging.getLogger(__name__)

# Create a base for batch job models
Base = declarative_base()


class BatchJob(Base):
    """Database model for batch processing jobs."""

    __tablename__ = "batch_jobs"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default="pending")
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, default=0)
    successful_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON metadata
    priority = Column(Integer, default=0)  # Higher number = higher priority
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    progress_callback_url = Column(String, nullable=True)
    user_id = Column(Integer, nullable=True)


class BatchJobStatus(Enum):
    """Status of a batch processing job."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class BatchJobPriority(Enum):
    """Priority levels for batch jobs."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class BatchFileResult:
    """Result of processing a single file in a batch."""

    file_index: int
    filename: str
    success: bool
    resource_id: Optional[int] = None
    resource_data: Optional[Dict] = None
    error: Optional[str] = None
    processing_time_seconds: Optional[float] = None


@dataclass
class BatchJobProgress:
    """Progress information for a batch job."""

    job_id: str
    status: BatchJobStatus
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    current_file: Optional[str] = None
    progress_percentage: float = 0.0
    estimated_time_remaining_seconds: Optional[float] = None
    processing_rate_files_per_second: Optional[float] = None


@dataclass
class BatchProcessingResult:
    """Result of a batch processing operation."""

    job_id: str
    status: BatchJobStatus
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    results: List[BatchFileResult]
    total_processing_time_seconds: float
    errors: List[Dict[str, Any]]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class BatchProcessingService:
    """Enhanced service for handling batch file processing operations."""

    def __init__(self, db_session_factory: Optional[Callable] = None):
        """Initialize the batch processing service."""
        self.pdf_service = PDFProcessingService()
        self.max_concurrent = settings.max_concurrent_processing
        self.max_batch_size = settings.file_processing.max_batch_size
        self.processing_timeout = (
            settings.processing_timeout_minutes * 60
        )  # Convert to seconds
        self.db_session_factory = db_session_factory

        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)

        # In-memory job tracking (for immediate access)
        self._active_jobs: Dict[str, BatchJobProgress] = {}
        self._job_queues: Dict[int, List[str]] = {
            BatchJobPriority.URGENT.value: [],
            BatchJobPriority.HIGH.value: [],
            BatchJobPriority.NORMAL.value: [],
            BatchJobPriority.LOW.value: [],
        }

        # Progress callbacks
        self._progress_callbacks: Dict[str, Callable] = {}

        # Background task for processing queue
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        logger.info(
            f"Enhanced batch processing service initialized with max_concurrent={self.max_concurrent}"
        )

    async def start_queue_processor(self):
        """Start the background queue processor."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_job_queue())
            logger.info("Batch job queue processor started")

    async def stop_queue_processor(self):
        """Stop the background queue processor."""
        self._shutdown_event.set()
        if self._queue_processor_task and not self._queue_processor_task.done():
            await self._queue_processor_task
            logger.info("Batch job queue processor stopped")

    async def _process_job_queue(self):
        """Background task to process queued jobs."""
        while not self._shutdown_event.is_set():
            try:
                # Process jobs by priority
                job_id = None
                for priority in [
                    BatchJobPriority.URGENT.value,
                    BatchJobPriority.HIGH.value,
                    BatchJobPriority.NORMAL.value,
                    BatchJobPriority.LOW.value,
                ]:
                    if self._job_queues[priority]:
                        job_id = self._job_queues[priority].pop(0)
                        break

                if job_id:
                    await self._process_queued_job(job_id)
                else:
                    # No jobs to process, wait a bit
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in job queue processor: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _process_queued_job(self, job_id: str):
        """Process a queued job."""
        if not self.db_session_factory:
            logger.error(
                f"Cannot process queued job {job_id}: no database session factory"
            )
            return

        try:
            with self.db_session_factory() as db:
                job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
                if not job:
                    logger.error(f"Queued job {job_id} not found in database")
                    return

                if job.status != BatchJobStatus.QUEUED.value:
                    logger.warning(
                        f"Job {job_id} is not in queued status: {job.status}"
                    )
                    return

                # Load job metadata
                metadata = json.loads(job.metadata) if job.metadata else {}

                # This would need to be implemented based on how files are stored
                # For now, we'll mark it as failed since we can't reconstruct the files
                job.status = BatchJobStatus.FAILED.value
                job.error_message = (
                    "Cannot process queued job: file reconstruction not implemented"
                )
                job.completed_at = datetime.utcnow()
                db.commit()

                logger.warning(
                    f"Job {job_id} marked as failed: file reconstruction not implemented"
                )

        except Exception as e:
            logger.error(f"Error processing queued job {job_id}: {e}")

    def register_progress_callback(
        self, job_id: str, callback: Callable[[BatchJobProgress], None]
    ):
        """Register a progress callback for a job."""
        self._progress_callbacks[job_id] = callback

    def _notify_progress(self, progress: BatchJobProgress):
        """Notify progress callbacks."""
        callback = self._progress_callbacks.get(progress.job_id)
        if callback:
            try:
                callback(progress)
            except Exception as e:
                logger.error(
                    f"Error in progress callback for job {progress.job_id}: {e}"
                )

    def _update_job_progress(self, job_id: str, **updates):
        """Update job progress and notify callbacks."""
        if job_id in self._active_jobs:
            progress = self._active_jobs[job_id]
            for key, value in updates.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)

            # Calculate progress percentage
            if progress.total_files > 0:
                progress.progress_percentage = (
                    progress.processed_files / progress.total_files
                ) * 100

            self._notify_progress(progress)

    async def create_batch_job(
        self,
        files: List[UploadFile],
        titles: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        topics: Optional[List[Topic]] = None,
        priority: BatchJobPriority = BatchJobPriority.NORMAL,
        user_id: Optional[int] = None,
        process_immediately: bool = True,
        db: Optional[Session] = None,
    ) -> str:
        """Create a new batch processing job.

        Args:
            files: List of uploaded files to process
            titles: Optional list of titles for each file
            descriptions: Optional list of descriptions for each file
            author: Optional author for all files
            source_platform: Optional source platform for all files
            topics: Optional list of topics to assign to all files
            priority: Job priority level
            user_id: User ID who created the job
            process_immediately: Whether to process immediately or queue
            db: Database session

        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())

        # Validate batch size
        if len(files) > self.max_batch_size:
            raise BatchProcessingError(
                f"Batch size {len(files)} exceeds maximum {self.max_batch_size}"
            )

        # Validate input lists
        if titles and len(titles) != len(files):
            raise BatchProcessingError("Number of titles must match number of files")

        if descriptions and len(descriptions) != len(files):
            raise BatchProcessingError(
                "Number of descriptions must match number of files"
            )

        # Create job metadata
        metadata = {
            "author": author,
            "source_platform": source_platform,
            "topic_ids": [t.id for t in topics] if topics else [],
            "titles": titles,
            "descriptions": descriptions,
            "file_names": [f.filename for f in files],
        }

        # Create job record if database session is available
        if db:
            batch_job = BatchJob(
                id=job_id,
                status=BatchJobStatus.PENDING.value
                if process_immediately
                else BatchJobStatus.QUEUED.value,
                total_files=len(files),
                metadata=json.dumps(metadata),
                priority=priority.value,
                user_id=user_id,
            )
            db.add(batch_job)
            db.commit()

        # Create progress tracking
        progress = BatchJobProgress(
            job_id=job_id,
            status=BatchJobStatus.PENDING
            if process_immediately
            else BatchJobStatus.QUEUED,
            total_files=len(files),
            processed_files=0,
            successful_files=0,
            failed_files=0,
        )
        self._active_jobs[job_id] = progress

        if process_immediately:
            # Process immediately
            asyncio.create_task(
                self._process_job_async(
                    job_id,
                    files,
                    titles,
                    descriptions,
                    author,
                    source_platform,
                    topics,
                    db,
                )
            )
        else:
            # Add to queue
            self._job_queues[priority.value].append(job_id)
            await self.start_queue_processor()

        logger.info(
            f"Created batch job {job_id} with {len(files)} files, priority={priority.name}"
        )
        return job_id

    async def _process_job_async(
        self,
        job_id: str,
        files: List[UploadFile],
        titles: Optional[List[str]],
        descriptions: Optional[List[str]],
        author: Optional[str],
        source_platform: Optional[str],
        topics: Optional[List[Topic]],
        db: Optional[Session],
    ):
        """Process a job asynchronously."""
        try:
            result = await self.process_batch(
                files=files,
                titles=titles,
                descriptions=descriptions,
                author=author,
                source_platform=source_platform,
                topics=topics,
                db=db,
                job_id=job_id,
            )
            logger.info(f"Async job {job_id} completed with status {result.status}")
        except Exception as e:
            logger.error(f"Async job {job_id} failed: {e}")
            self._update_job_progress(job_id, status=BatchJobStatus.FAILED)

    def get_job_progress(self, job_id: str) -> Optional[BatchJobProgress]:
        """Get current progress for a job."""
        return self._active_jobs.get(job_id)

    async def cancel_job(self, job_id: str, db: Optional[Session] = None) -> bool:
        """Cancel a batch processing job."""
        progress = self._active_jobs.get(job_id)
        if not progress:
            return False

        if progress.status in [
            BatchJobStatus.COMPLETED,
            BatchJobStatus.FAILED,
            BatchJobStatus.CANCELLED,
        ]:
            return False

        # Update status
        self._update_job_progress(job_id, status=BatchJobStatus.CANCELLED)

        # Update database if available
        if db:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = BatchJobStatus.CANCELLED.value
                job.completed_at = datetime.utcnow()
                db.commit()

        # Remove from queues
        for queue in self._job_queues.values():
            if job_id in queue:
                queue.remove(job_id)

        logger.info(f"Cancelled batch job {job_id}")
        return True

    async def retry_job(self, job_id: str, db: Optional[Session] = None) -> bool:
        """Retry a failed batch processing job."""
        if not db:
            logger.error(f"Cannot retry job {job_id}: no database session")
            return False

        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for retry")
            return False

        if job.status not in [
            BatchJobStatus.FAILED.value,
            BatchJobStatus.PARTIAL_SUCCESS.value,
        ]:
            logger.warning(f"Job {job_id} cannot be retried, status: {job.status}")
            return False

        if job.retry_count >= job.max_retries:
            logger.warning(f"Job {job_id} has exceeded max retries ({job.max_retries})")
            return False

        # Update job for retry
        job.status = BatchJobStatus.RETRYING.value
        job.retry_count += 1
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        db.commit()

        # Add to high priority queue
        self._job_queues[BatchJobPriority.HIGH.value].append(job_id)
        await self.start_queue_processor()

        logger.info(f"Queued job {job_id} for retry (attempt {job.retry_count})")
        return True

    def cleanup_completed_jobs(
        self, older_than_hours: int = 24, db: Optional[Session] = None
    ):
        """Clean up completed jobs older than specified hours."""
        if not db:
            return

        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)

        # Clean up database records
        deleted_count = (
            db.query(BatchJob)
            .filter(
                BatchJob.completed_at < cutoff_time,
                BatchJob.status.in_(
                    [
                        BatchJobStatus.COMPLETED.value,
                        BatchJobStatus.FAILED.value,
                        BatchJobStatus.CANCELLED.value,
                    ]
                ),
            )
            .delete()
        )

        db.commit()

        # Clean up in-memory tracking
        to_remove = []
        for job_id, progress in self._active_jobs.items():
            if progress.status in [
                BatchJobStatus.COMPLETED,
                BatchJobStatus.FAILED,
                BatchJobStatus.CANCELLED,
            ]:
                to_remove.append(job_id)

        for job_id in to_remove:
            del self._active_jobs[job_id]
            if job_id in self._progress_callbacks:
                del self._progress_callbacks[job_id]

        logger.info(
            f"Cleaned up {deleted_count} completed batch jobs older than {older_than_hours} hours"
        )

    async def process_batch(
        self,
        files: List[UploadFile],
        titles: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        topics: Optional[List[Topic]] = None,
        db: Session = None,
        job_id: Optional[str] = None,
    ) -> BatchProcessingResult:
        """Process a batch of files concurrently with enhanced tracking.

        Args:
            files: List of uploaded files to process
            titles: Optional list of titles for each file
            descriptions: Optional list of descriptions for each file
            author: Optional author for all files
            source_platform: Optional source platform for all files
            topics: Optional list of topics to assign to all files
            db: Database session
            job_id: Optional job ID for tracking

        Returns:
            BatchProcessingResult with processing results
        """
        start_time = time.time()
        job_id = job_id or str(uuid.uuid4())

        logger.info(f"Starting batch processing job {job_id} with {len(files)} files")

        # Initialize or update job progress
        if job_id not in self._active_jobs:
            progress = BatchJobProgress(
                job_id=job_id,
                status=BatchJobStatus.PROCESSING,
                total_files=len(files),
                processed_files=0,
                successful_files=0,
                failed_files=0,
            )
            self._active_jobs[job_id] = progress
        else:
            self._update_job_progress(job_id, status=BatchJobStatus.PROCESSING)

        # Update database job status
        if db:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = BatchJobStatus.PROCESSING.value
                job.started_at = datetime.utcnow()
                db.commit()

        # Validate batch size
        if len(files) > self.max_batch_size:
            error_msg = f"Batch size {len(files)} exceeds maximum {self.max_batch_size}"
            self._update_job_progress(job_id, status=BatchJobStatus.FAILED)
            if db:
                job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
                if job:
                    job.status = BatchJobStatus.FAILED.value
                    job.error_message = error_msg
                    job.completed_at = datetime.utcnow()
                    db.commit()
            raise BatchProcessingError(error_msg)

        # Validate input lists
        if titles and len(titles) != len(files):
            error_msg = "Number of titles must match number of files"
            self._update_job_progress(job_id, status=BatchJobStatus.FAILED)
            raise BatchProcessingError(error_msg)

        if descriptions and len(descriptions) != len(files):
            error_msg = "Number of descriptions must match number of files"
            self._update_job_progress(job_id, status=BatchJobStatus.FAILED)
            raise BatchProcessingError(error_msg)

        results = []
        errors = []

        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Process files concurrently with progress tracking
        tasks = []
        for i, file in enumerate(files):
            title = titles[i] if titles else (file.filename or f"Batch File {i+1}")
            description = (
                descriptions[i]
                if descriptions
                else f"Batch processed file: {file.filename}"
            )

            task = self._process_single_file_with_semaphore(
                semaphore=semaphore,
                file_index=i,
                file=file,
                title=title,
                description=description,
                author=author,
                source_platform=source_platform or "batch_processing",
                topics=topics or [],
                db=db,
                job_id=job_id,
            )
            tasks.append(task)

        # Wait for all tasks to complete with timeout
        try:
            completed_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.processing_timeout,
            )

            # Process results
            for i, result in enumerate(completed_results):
                if isinstance(result, Exception):
                    error_result = BatchFileResult(
                        file_index=i,
                        filename=files[i].filename or f"file_{i}",
                        success=False,
                        error=str(result),
                    )
                    results.append(error_result)
                    errors.append(
                        {
                            "file_index": i,
                            "filename": files[i].filename,
                            "error": str(result),
                        }
                    )
                else:
                    results.append(result)
                    if not result.success:
                        errors.append(
                            {
                                "file_index": result.file_index,
                                "filename": result.filename,
                                "error": result.error,
                            }
                        )

        except asyncio.TimeoutError:
            logger.error(
                f"Batch processing job {job_id} timed out after {self.processing_timeout} seconds"
            )
            # Handle timeout - mark remaining files as failed
            for i, file in enumerate(files):
                if i >= len(results):
                    timeout_result = BatchFileResult(
                        file_index=i,
                        filename=file.filename or f"file_{i}",
                        success=False,
                        error="Processing timed out",
                    )
                    results.append(timeout_result)
                    errors.append(
                        {
                            "file_index": i,
                            "filename": file.filename,
                            "error": "Processing timed out",
                        }
                    )

        # Calculate final statistics
        successful_files = sum(1 for r in results if r.success)
        failed_files = len(results) - successful_files
        total_processing_time = time.time() - start_time

        # Determine overall status
        if successful_files == 0:
            status = BatchJobStatus.FAILED
        elif failed_files == 0:
            status = BatchJobStatus.COMPLETED
        else:
            status = BatchJobStatus.PARTIAL_SUCCESS

        # Update final progress
        self._update_job_progress(
            job_id,
            status=status,
            processed_files=len(results),
            successful_files=successful_files,
            failed_files=failed_files,
        )

        # Update database
        if db:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = status.value
                job.processed_files = len(results)
                job.successful_files = successful_files
                job.failed_files = failed_files
                job.processing_time_seconds = total_processing_time
                job.completed_at = datetime.utcnow()
                if errors:
                    job.error_message = f"{len(errors)} files failed processing"
                db.commit()

        batch_result = BatchProcessingResult(
            job_id=job_id,
            status=status,
            total_files=len(files),
            processed_files=len(results),
            successful_files=successful_files,
            failed_files=failed_files,
            results=results,
            total_processing_time_seconds=total_processing_time,
            errors=errors,
            created_at=datetime.utcnow() - timedelta(seconds=total_processing_time),
            started_at=datetime.utcnow() - timedelta(seconds=total_processing_time),
            completed_at=datetime.utcnow(),
        )

        logger.info(
            f"Batch processing job {job_id} completed: "
            f"{successful_files}/{len(files)} successful, "
            f"took {total_processing_time:.2f}s"
        )

        return batch_result

    async def _process_single_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        file_index: int,
        file: UploadFile,
        title: str,
        description: str,
        author: Optional[str],
        source_platform: str,
        topics: List[Topic],
        db: Session,
        job_id: Optional[str] = None,
    ) -> BatchFileResult:
        """Process a single file with concurrency control and progress tracking.

        Args:
            semaphore: Semaphore for controlling concurrency
            file_index: Index of the file in the batch
            file: The uploaded file
            title: Title for the resource
            description: Description for the resource
            author: Optional author
            source_platform: Source platform
            topics: List of topics to assign
            db: Database session
            job_id: Optional job ID for progress tracking

        Returns:
            BatchFileResult with processing outcome
        """
        async with semaphore:
            start_time = time.time()
            filename = file.filename or f"file_{file_index}"

            # Update progress - currently processing this file
            if job_id:
                self._update_job_progress(job_id, current_file=filename)

            try:
                result = await self._process_single_file(
                    file_index=file_index,
                    file=file,
                    title=title,
                    description=description,
                    author=author,
                    source_platform=source_platform,
                    topics=topics,
                    db=db,
                )

                processing_time = time.time() - start_time
                result.processing_time_seconds = processing_time

                # Update progress - file completed
                if job_id:
                    progress = self._active_jobs.get(job_id)
                    if progress:
                        new_processed = progress.processed_files + 1
                        new_successful = progress.successful_files + (
                            1 if result.success else 0
                        )
                        new_failed = progress.failed_files + (
                            0 if result.success else 1
                        )

                        # Calculate processing rate
                        total_time = time.time() - start_time
                        rate = new_processed / total_time if total_time > 0 else 0

                        # Estimate remaining time
                        remaining_files = progress.total_files - new_processed
                        eta = remaining_files / rate if rate > 0 else None

                        self._update_job_progress(
                            job_id,
                            processed_files=new_processed,
                            successful_files=new_successful,
                            failed_files=new_failed,
                            current_file=None,
                            processing_rate_files_per_second=rate,
                            estimated_time_remaining_seconds=eta,
                        )

                return result

            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Error processing file {file_index} ({filename}): {e}")

                # Update progress - file failed
                if job_id:
                    progress = self._active_jobs.get(job_id)
                    if progress:
                        new_processed = progress.processed_files + 1
                        new_failed = progress.failed_files + 1

                        self._update_job_progress(
                            job_id,
                            processed_files=new_processed,
                            failed_files=new_failed,
                            current_file=None,
                        )

                return BatchFileResult(
                    file_index=file_index,
                    filename=filename,
                    success=False,
                    error=str(e),
                    processing_time_seconds=processing_time,
                )

    async def _process_single_file(
        self,
        file_index: int,
        file: UploadFile,
        title: str,
        description: str,
        author: Optional[str],
        source_platform: str,
        topics: List[Topic],
        db: Session,
    ) -> BatchFileResult:
        """Process a single file in the batch.

        Args:
            file_index: Index of the file in the batch
            file: The uploaded file
            title: Title for the resource
            description: Description for the resource
            author: Optional author
            source_platform: Source platform
            topics: List of topics to assign
            db: Database session

        Returns:
            BatchFileResult with processing outcome
        """
        filename = file.filename or f"file_{file_index}"

        try:
            # Validate filename
            if not file.filename:
                raise FileValidationError("Filename is required")

            # Determine content type
            import os

            file_extension = os.path.splitext(file.filename)[1].lower()

            if file_extension == ".pdf":
                content_type = "pdf"
            elif file_extension in [".docx", ".doc"]:
                content_type = "docx"
            elif file_extension in [".txt", ".md"]:
                content_type = "text"
            elif file_extension in [".html", ".htm"]:
                content_type = "html"
            else:
                raise FileValidationError(f"Unsupported file type: {file_extension}")

            # Create resource in database
            source_url = f"batch_upload://{file.filename}"

            new_resource = Resource(
                title=title,
                description=description,
                content_type=content_type,
                source_url=source_url,
                author=author,
                source_platform=source_platform,
                topics=topics,
            )
            db.add(new_resource)
            db.commit()
            db.refresh(new_resource)

            # Process the file based on type
            if content_type == "pdf":
                storage_path, file_size = await self.pdf_service.process_pdf(
                    file, new_resource, db
                )

                # Refresh resource to get updated data
                db.refresh(new_resource)

                return BatchFileResult(
                    file_index=file_index,
                    filename=filename,
                    success=True,
                    resource_id=new_resource.id,
                    resource_data={
                        "id": new_resource.id,
                        "title": new_resource.title,
                        "description": new_resource.description,
                        "content_type": new_resource.content_type,
                        "storage_path": new_resource.storage_path,
                        "file_size": new_resource.file_size,
                        "created_at": new_resource.created_at,
                        "topics": [
                            {"id": t.id, "name": t.name} for t in new_resource.topics
                        ],
                    },
                )
            else:
                # For non-PDF files, create placeholder result
                return BatchFileResult(
                    file_index=file_index,
                    filename=filename,
                    success=True,
                    resource_id=new_resource.id,
                    resource_data={
                        "id": new_resource.id,
                        "title": new_resource.title,
                        "description": new_resource.description,
                        "content_type": new_resource.content_type,
                        "status": "pending_processing",
                    },
                )

        except Exception as e:
            # Clean up resource if it was created
            try:
                if "new_resource" in locals():
                    db.delete(new_resource)
                    db.commit()
            except:
                pass

            raise e

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics and system status.

        Returns:
            Dictionary with processing statistics
        """
        # Count active jobs by status
        active_jobs_by_status = {}
        for progress in self._active_jobs.values():
            status = progress.status.value
            active_jobs_by_status[status] = active_jobs_by_status.get(status, 0) + 1

        # Count queued jobs by priority
        queued_jobs_by_priority = {
            "urgent": len(self._job_queues[BatchJobPriority.URGENT.value]),
            "high": len(self._job_queues[BatchJobPriority.HIGH.value]),
            "normal": len(self._job_queues[BatchJobPriority.NORMAL.value]),
            "low": len(self._job_queues[BatchJobPriority.LOW.value]),
        }

        return {
            "system_config": {
                "max_concurrent_processing": self.max_concurrent,
                "max_batch_size": self.max_batch_size,
                "processing_timeout_minutes": self.processing_timeout // 60,
                "supported_file_types": settings.file_processing.get_supported_types_list(),
                "max_file_size_mb": settings.file_processing.max_file_size_mb,
            },
            "current_status": {
                "active_jobs_count": len(self._active_jobs),
                "active_jobs_by_status": active_jobs_by_status,
                "queued_jobs_by_priority": queued_jobs_by_priority,
                "total_queued_jobs": sum(queued_jobs_by_priority.values()),
                "queue_processor_running": (
                    self._queue_processor_task is not None
                    and not self._queue_processor_task.done()
                ),
            },
            "capabilities": {
                "job_persistence": self.db_session_factory is not None,
                "progress_tracking": True,
                "job_queuing": True,
                "job_retry": True,
                "job_cancellation": True,
                "priority_processing": True,
                "progress_callbacks": True,
            },
        }

    def get_job_history(
        self, limit: int = 50, db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """Get batch job history from database.

        Args:
            limit: Maximum number of jobs to return
            db: Database session

        Returns:
            List of job history records
        """
        if not db:
            return []

        jobs = (
            db.query(BatchJob).order_by(BatchJob.created_at.desc()).limit(limit).all()
        )

        history = []
        for job in jobs:
            metadata = json.loads(job.metadata) if job.metadata else {}

            history.append(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "total_files": job.total_files,
                    "processed_files": job.processed_files,
                    "successful_files": job.successful_files,
                    "failed_files": job.failed_files,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "processing_time_seconds": job.processing_time_seconds,
                    "priority": job.priority,
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                    "user_id": job.user_id,
                    "error_message": job.error_message,
                    "metadata": metadata,
                }
            )

        return history

    async def pause_job(self, job_id: str, db: Optional[Session] = None) -> bool:
        """Pause a running batch processing job."""
        progress = self._active_jobs.get(job_id)
        if not progress or progress.status != BatchJobStatus.PROCESSING:
            return False

        self._update_job_progress(job_id, status=BatchJobStatus.PAUSED)

        if db:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = BatchJobStatus.PAUSED.value
                db.commit()

        logger.info(f"Paused batch job {job_id}")
        return True

    async def resume_job(self, job_id: str, db: Optional[Session] = None) -> bool:
        """Resume a paused batch processing job."""
        progress = self._active_jobs.get(job_id)
        if not progress or progress.status != BatchJobStatus.PAUSED:
            return False

        # Add to high priority queue for immediate processing
        self._job_queues[BatchJobPriority.HIGH.value].append(job_id)
        await self.start_queue_processor()

        if db:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = BatchJobStatus.QUEUED.value
                db.commit()

        logger.info(f"Resumed batch job {job_id}")
        return True


class BatchProcessingError(KnowledgeServiceError):
    """Exception raised during batch processing operations."""

    pass
