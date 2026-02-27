#!/usr/bin/env python3
"""
Demonstration of enhanced batch processing capabilities.

This script shows how to use the enhanced batch processing service
with job tracking, progress monitoring, and queue management.
"""

import asyncio
import os
# Import the enhanced batch processing service
import sys
import time
from typing import List
from unittest.mock import Mock

from fastapi import UploadFile

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from knowledge_service.services.batch_processing import (
    BatchJobPriority, BatchJobProgress, BatchJobStatus, BatchProcessingService)


class MockUploadFile:
    """Mock upload file for demonstration."""

    def __init__(self, filename: str, content: bytes = b"mock content"):
        self.filename = filename
        self.content = content

    async def read(self) -> bytes:
        return self.content


async def progress_callback(progress: BatchJobProgress):
    """Example progress callback function."""
    print(
        f"Job {progress.job_id}: {progress.status.value} - "
        f"{progress.processed_files}/{progress.total_files} files "
        f"({progress.progress_percentage:.1f}%)"
    )

    if progress.current_file:
        print(f"  Currently processing: {progress.current_file}")

    if progress.processing_rate_files_per_second:
        print(
            f"  Processing rate: {progress.processing_rate_files_per_second:.2f} files/sec"
        )

    if progress.estimated_time_remaining_seconds:
        print(f"  ETA: {progress.estimated_time_remaining_seconds:.0f} seconds")


async def demonstrate_basic_batch_processing():
    """Demonstrate basic batch processing with progress tracking."""
    print("=== Basic Batch Processing Demo ===")

    # Create batch processing service
    service = BatchProcessingService()

    # Create mock files
    files = [MockUploadFile(f"document_{i}.pdf") for i in range(5)]

    # Create batch job with immediate processing
    job_id = await service.create_batch_job(
        files=files,
        titles=[f"Document {i}" for i in range(5)],
        descriptions=[f"Test document {i}" for i in range(5)],
        author="Demo User",
        source_platform="demo",
        priority=BatchJobPriority.NORMAL,
        process_immediately=False,  # Queue for demonstration
    )

    print(f"Created batch job: {job_id}")

    # Register progress callback
    service.register_progress_callback(job_id, progress_callback)

    # Monitor progress
    while True:
        progress = service.get_job_progress(job_id)
        if not progress:
            print("Job not found or completed")
            break

        if progress.status in [
            BatchJobStatus.COMPLETED,
            BatchJobStatus.FAILED,
            BatchJobStatus.PARTIAL_SUCCESS,
            BatchJobStatus.CANCELLED,
        ]:
            print(f"Job finished with status: {progress.status.value}")
            break

        await asyncio.sleep(1)

    print()


async def demonstrate_priority_queuing():
    """Demonstrate priority-based job queuing."""
    print("=== Priority Queuing Demo ===")

    service = BatchProcessingService()

    # Create jobs with different priorities
    priorities = [
        (BatchJobPriority.LOW, "Low priority job"),
        (BatchJobPriority.NORMAL, "Normal priority job"),
        (BatchJobPriority.HIGH, "High priority job"),
        (BatchJobPriority.URGENT, "Urgent priority job"),
    ]

    job_ids = []

    for priority, description in priorities:
        files = [MockUploadFile(f"{description.lower().replace(' ', '_')}.pdf")]

        job_id = await service.create_batch_job(
            files=files,
            titles=[description],
            priority=priority,
            process_immediately=False,
        )

        job_ids.append((job_id, priority.name, description))
        print(f"Queued {description} (Priority: {priority.name})")

    # Show queue statistics
    stats = service.get_processing_stats()
    queue_stats = stats["current_status"]["queued_jobs_by_priority"]

    print("\nQueue Statistics:")
    for priority_name, count in queue_stats.items():
        if count > 0:
            print(f"  {priority_name.capitalize()}: {count} jobs")

    print(f"Total queued jobs: {stats['current_status']['total_queued_jobs']}")
    print()


async def demonstrate_job_management():
    """Demonstrate job management operations."""
    print("=== Job Management Demo ===")

    service = BatchProcessingService()

    # Create a job for management demonstration
    files = [MockUploadFile(f"management_test_{i}.pdf") for i in range(3)]

    job_id = await service.create_batch_job(
        files=files,
        titles=["Management Test 1", "Management Test 2", "Management Test 3"],
        priority=BatchJobPriority.NORMAL,
        process_immediately=False,
    )

    print(f"Created job for management demo: {job_id}")

    # Demonstrate pause
    print("Pausing job...")
    success = await service.pause_job(job_id)
    print(f"Pause successful: {success}")

    progress = service.get_job_progress(job_id)
    if progress:
        print(f"Job status after pause: {progress.status.value}")

    # Demonstrate resume
    print("Resuming job...")
    success = await service.resume_job(job_id)
    print(f"Resume successful: {success}")

    # Demonstrate cancellation
    print("Cancelling job...")
    success = await service.cancel_job(job_id)
    print(f"Cancellation successful: {success}")

    progress = service.get_job_progress(job_id)
    if progress:
        print(f"Final job status: {progress.status.value}")

    print()


def demonstrate_statistics():
    """Demonstrate comprehensive statistics."""
    print("=== Statistics Demo ===")

    service = BatchProcessingService()

    # Add some mock jobs for statistics
    from knowledge_service.services.batch_processing import BatchJobProgress

    service._active_jobs["demo-processing"] = BatchJobProgress(
        job_id="demo-processing",
        status=BatchJobStatus.PROCESSING,
        total_files=10,
        processed_files=6,
        successful_files=5,
        failed_files=1,
    )

    service._active_jobs["demo-completed"] = BatchJobProgress(
        job_id="demo-completed",
        status=BatchJobStatus.COMPLETED,
        total_files=5,
        processed_files=5,
        successful_files=5,
        failed_files=0,
    )

    # Add some queued jobs
    service._job_queues[BatchJobPriority.HIGH.value].extend(["queued-1", "queued-2"])
    service._job_queues[BatchJobPriority.NORMAL.value].append("queued-3")

    stats = service.get_processing_stats()

    print("System Configuration:")
    system_config = stats["system_config"]
    for key, value in system_config.items():
        print(f"  {key}: {value}")

    print("\nCurrent Status:")
    current_status = stats["current_status"]
    print(f"  Active jobs: {current_status['active_jobs_count']}")
    print(f"  Total queued jobs: {current_status['total_queued_jobs']}")

    print("\n  Active jobs by status:")
    for status, count in current_status["active_jobs_by_status"].items():
        print(f"    {status}: {count}")

    print("\n  Queued jobs by priority:")
    for priority, count in current_status["queued_jobs_by_priority"].items():
        if count > 0:
            print(f"    {priority}: {count}")

    print("\nCapabilities:")
    capabilities = stats["capabilities"]
    for capability, enabled in capabilities.items():
        status = "✓" if enabled else "✗"
        print(f"  {status} {capability.replace('_', ' ').title()}")

    print()


async def main():
    """Run all demonstrations."""
    print("Enhanced Batch Processing Service Demonstration")
    print("=" * 50)
    print()

    try:
        await demonstrate_basic_batch_processing()
        await demonstrate_priority_queuing()
        await demonstrate_job_management()
        demonstrate_statistics()

        print("Demo completed successfully!")

    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
