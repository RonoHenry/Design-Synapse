# Enhanced Batch Processing Documentation

## Overview

The Knowledge Service now includes comprehensive batch processing capabilities for handling multiple file uploads and processing operations efficiently. This system provides job tracking, progress monitoring, priority queuing, and robust error handling.

## Key Features

### 1. Job Status Tracking and Persistence
- **Database Persistence**: Jobs are stored in the database for durability
- **Status Tracking**: Real-time status updates (pending, queued, processing, completed, failed, etc.)
- **Progress Monitoring**: Detailed progress information with percentage completion
- **Job History**: Complete history of all batch processing jobs

### 2. Priority-Based Queue Management
- **Four Priority Levels**: Urgent, High, Normal, Low
- **Queue Processing**: Background queue processor handles jobs by priority
- **Concurrent Processing**: Configurable concurrent job processing
- **Queue Statistics**: Real-time queue status and statistics

### 3. Job Management Operations
- **Pause/Resume**: Pause running jobs and resume them later
- **Cancellation**: Cancel jobs at any stage
- **Retry Logic**: Automatic retry for failed jobs with configurable limits
- **Job Cleanup**: Automatic cleanup of old completed jobs

### 4. Progress Monitoring and Callbacks
- **Real-time Progress**: Live progress updates with file-level tracking
- **Progress Callbacks**: Register callbacks for progress notifications
- **Processing Rate**: Calculate and display processing rates
- **ETA Calculation**: Estimated time remaining for job completion

### 5. Enhanced Error Handling
- **Detailed Error Reporting**: Comprehensive error information per file
- **Partial Success Handling**: Handle scenarios where some files succeed
- **Timeout Management**: Configurable timeouts with graceful handling
- **Retry Mechanisms**: Intelligent retry logic for transient failures

## API Endpoints

### Create Batch Job
```http
POST /api/v1/resources/batch/create
```

Create a new batch processing job with enhanced options.

**Parameters:**
- `files`: List of files to process
- `titles`: Comma-separated titles (optional)
- `descriptions`: Comma-separated descriptions (optional)
- `author`: Author for all files (optional)
- `source_platform`: Source platform (optional)
- `topic_ids`: Comma-separated topic IDs (optional)
- `priority`: Job priority (low, normal, high, urgent)
- `process_immediately`: Whether to process immediately or queue

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "processing|queued",
  "total_files": 5,
  "priority": "normal",
  "process_immediately": true,
  "message": "Batch job created with 5 files"
}
```

### Get Job Progress
```http
GET /api/v1/resources/batch/jobs/{job_id}/progress
```

Get real-time progress for a batch processing job.

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "processing",
  "total_files": 10,
  "processed_files": 6,
  "successful_files": 5,
  "failed_files": 1,
  "current_file": "document.pdf",
  "progress_percentage": 60.0,
  "estimated_time_remaining_seconds": 120,
  "processing_rate_files_per_second": 0.5
}
```

### Job Management Operations

#### Cancel Job
```http
POST /api/v1/resources/batch/jobs/{job_id}/cancel
```

#### Retry Job
```http
POST /api/v1/resources/batch/jobs/{job_id}/retry
```

#### Pause Job
```http
POST /api/v1/resources/batch/jobs/{job_id}/pause
```

#### Resume Job
```http
POST /api/v1/resources/batch/jobs/{job_id}/resume
```

### Job History
```http
GET /api/v1/resources/batch/jobs/history?limit=50
```

Get batch processing job history.

**Response:**
```json
{
  "total": 25,
  "limit": 50,
  "jobs": [
    {
      "job_id": "uuid-string",
      "status": "completed",
      "total_files": 5,
      "processed_files": 5,
      "successful_files": 4,
      "failed_files": 1,
      "created_at": "2024-01-01T12:00:00Z",
      "started_at": "2024-01-01T12:00:05Z",
      "completed_at": "2024-01-01T12:05:30Z",
      "processing_time_seconds": 325.0,
      "priority": 1,
      "retry_count": 0,
      "user_id": 123,
      "error_message": null,
      "metadata": {
        "author": "John Doe",
        "source_platform": "upload"
      }
    }
  ]
}
```

### System Statistics
```http
GET /api/v1/resources/batch/stats
```

Get comprehensive batch processing statistics.

**Response:**
```json
{
  "system_config": {
    "max_concurrent_processing": 3,
    "max_batch_size": 10,
    "processing_timeout_minutes": 30,
    "supported_file_types": ["pdf", "docx", "txt"],
    "max_file_size_mb": 50
  },
  "current_status": {
    "active_jobs_count": 5,
    "active_jobs_by_status": {
      "processing": 2,
      "completed": 2,
      "failed": 1
    },
    "queued_jobs_by_priority": {
      "urgent": 0,
      "high": 2,
      "normal": 3,
      "low": 1
    },
    "total_queued_jobs": 6,
    "queue_processor_running": true
  },
  "capabilities": {
    "job_persistence": true,
    "progress_tracking": true,
    "job_queuing": true,
    "job_retry": true,
    "job_cancellation": true,
    "priority_processing": true,
    "progress_callbacks": true
  }
}
```

### Cleanup Jobs
```http
DELETE /api/v1/resources/batch/jobs/cleanup?older_than_hours=24
```

Clean up completed batch jobs older than specified hours.

## Configuration

### Environment Variables

```bash
# Basic batch processing
MAX_CONCURRENT_PROCESSING=3
PROCESSING_TIMEOUT_MINUTES=30
FILE_MAX_BATCH_SIZE=10

# Enhanced batch processing
BATCH_JOB_CLEANUP_HOURS=24
BATCH_QUEUE_CHECK_INTERVAL_SECONDS=5
BATCH_PROGRESS_UPDATE_INTERVAL_SECONDS=2
BATCH_MAX_RETRY_ATTEMPTS=3
BATCH_ENABLE_PERSISTENCE=true
```

### Database Migration

The enhanced batch processing requires a database table for job persistence:

```sql
CREATE TABLE batch_jobs (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_files INTEGER NOT NULL,
    processed_files INTEGER DEFAULT 0,
    successful_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    processing_time_seconds FLOAT NULL,
    error_message TEXT NULL,
    metadata TEXT NULL,
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    progress_callback_url VARCHAR(500) NULL,
    user_id INTEGER NULL
);
```

## Usage Examples

### Python Service Usage

```python
from knowledge_service.services.batch_processing import (
    BatchProcessingService,
    BatchJobPriority
)

# Initialize service
service = BatchProcessingService(db_session_factory=get_db_session)

# Create batch job
job_id = await service.create_batch_job(
    files=uploaded_files,
    titles=file_titles,
    priority=BatchJobPriority.HIGH,
    user_id=current_user_id,
    process_immediately=False
)

# Register progress callback
def progress_callback(progress):
    print(f"Job {progress.job_id}: {progress.progress_percentage}% complete")

service.register_progress_callback(job_id, progress_callback)

# Monitor progress
progress = service.get_job_progress(job_id)
print(f"Status: {progress.status.value}")
print(f"Progress: {progress.progress_percentage}%")

# Manage job
await service.pause_job(job_id)
await service.resume_job(job_id)
await service.cancel_job(job_id)
```

### JavaScript/Frontend Usage

```javascript
// Create batch job
const formData = new FormData();
files.forEach(file => formData.append('files', file));
formData.append('priority', 'high');
formData.append('process_immediately', 'false');

const response = await fetch('/api/v1/resources/batch/create', {
    method: 'POST',
    body: formData
});

const { job_id } = await response.json();

// Monitor progress
const monitorProgress = async (jobId) => {
    const interval = setInterval(async () => {
        const response = await fetch(`/api/v1/resources/batch/jobs/${jobId}/progress`);
        const progress = await response.json();

        console.log(`Progress: ${progress.progress_percentage}%`);

        if (['completed', 'failed', 'cancelled'].includes(progress.status)) {
            clearInterval(interval);
            console.log(`Job finished with status: ${progress.status}`);
        }
    }, 2000);
};

monitorProgress(job_id);
```

## Job Status Flow

```
PENDING → QUEUED → PROCESSING → COMPLETED
                              → FAILED
                              → PARTIAL_SUCCESS
                              → CANCELLED
                              → PAUSED → QUEUED (resume)
                              → RETRYING → QUEUED
```

## Best Practices

### 1. File Size and Batch Size Management
- Keep batch sizes reasonable (recommended: 5-20 files)
- Monitor file sizes to avoid memory issues
- Use appropriate timeouts for large files

### 2. Priority Management
- Use URGENT sparingly for truly critical jobs
- Most jobs should use NORMAL priority
- Use LOW priority for background/maintenance jobs

### 3. Error Handling
- Implement proper error handling in callbacks
- Monitor failed jobs and investigate patterns
- Use retry functionality for transient failures

### 4. Resource Management
- Regular cleanup of old completed jobs
- Monitor queue sizes and processing rates
- Adjust concurrent processing based on system resources

### 5. Monitoring and Observability
- Use progress callbacks for real-time updates
- Monitor system statistics regularly
- Set up alerts for failed jobs or queue backlogs

## Troubleshooting

### Common Issues

1. **Jobs stuck in QUEUED status**
   - Check if queue processor is running
   - Verify database connectivity
   - Check system resource availability

2. **High failure rates**
   - Review file validation logic
   - Check processing timeouts
   - Verify storage availability

3. **Memory issues with large batches**
   - Reduce batch size
   - Increase system memory
   - Optimize file processing logic

4. **Slow processing**
   - Increase concurrent processing limit
   - Optimize file processing algorithms
   - Check database performance

### Debugging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('knowledge_service.services.batch_processing').setLevel(logging.DEBUG)
```

Check job history for patterns:

```python
service = BatchProcessingService()
history = service.get_job_history(limit=100, db=db_session)
failed_jobs = [job for job in history if job['status'] == 'failed']
```

## Performance Considerations

- **Concurrent Processing**: Balance between throughput and resource usage
- **Database Performance**: Index batch_jobs table appropriately
- **Memory Usage**: Monitor memory consumption with large files
- **Storage I/O**: Consider storage performance for file operations
- **Network**: Account for network latency in distributed setups

## Security Considerations

- **User Authorization**: Ensure users can only access their own jobs
- **File Validation**: Validate all uploaded files thoroughly
- **Resource Limits**: Enforce appropriate limits to prevent abuse
- **Audit Logging**: Log all batch processing activities
- **Data Privacy**: Handle sensitive data appropriately during processing
