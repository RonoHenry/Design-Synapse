"""
Unit tests for StorageClient.

Tests storage client functionality including S3 integration,
file upload, URL generation, and error handling.

Requirements tested:
- 6: Visual output storage and CDN delivery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import io

from ..client import StorageClient, StorageError, StorageConnectionError


class TestStorageClient:
    """Test StorageClient functionality."""

    def test_storage_client_initialization(self):
        """Test StorageClient can be initialized with configuration."""
        # Act
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Assert
        assert client.bucket_name == "test-bucket"
        assert client.region == "us-east-1"
        assert client._access_key == "test-key"
        assert client._secret_key == "test-secret"

    def test_storage_client_initialization_with_cdn_url(self):
        """Test StorageClient initialization with CDN URL."""
        # Act
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret",
            cdn_url="https://cdn.example.com"
        )

        # Assert
        assert client.cdn_url == "https://cdn.example.com"

    @patch('boto3.client')
    def test_upload_file_success(self, mock_boto_client):
        """Test successful file upload to S3."""
        # Arrange
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )
        
        file_content = b"test file content"
        file_obj = io.BytesIO(file_content)

        # Act
        result = client.upload_file(
            file_obj=file_obj,
            key="designs/floor_plan_123.png",
            content_type="image/png"
        )

        # Assert
        mock_s3.upload_fileobj.assert_called_once()
        assert result["key"] == "designs/floor_plan_123.png"
        assert result["bucket"] == "test-bucket"
        assert "url" in result
        assert result["size"] == len(file_content)

    @patch('boto3.client')
    def test_upload_file_with_compression(self, mock_boto_client):
        """Test file upload with image compression."""
        # Arrange
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )
        
        file_content = b"large image content" * 1000  # Simulate large image
        file_obj = io.BytesIO(file_content)

        # Act
        result = client.upload_file(
            file_obj=file_obj,
            key="designs/large_image.png",
            content_type="image/png",
            compress=True
        )

        # Assert
        mock_s3.upload_fileobj.assert_called_once()
        assert result["compressed"] is True
        assert result["original_size"] == len(file_content)
        assert result["compressed_size"] < len(file_content)

    @patch('boto3.client')
    def test_upload_file_s3_error(self, mock_boto_client):
        """Test file upload handles S3 errors."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.upload_fileobj.side_effect = Exception("S3 connection failed")
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )
        
        file_obj = io.BytesIO(b"test content")

        # Act & Assert
        with pytest.raises(StorageError, match="Failed to upload file"):
            client.upload_file(
                file_obj=file_obj,
                key="designs/test.png",
                content_type="image/png"
            )

    @patch('boto3.client')
    def test_generate_signed_url_success(self, mock_boto_client):
        """Test successful signed URL generation."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/designs/test.png?signature=abc123"
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Act
        url = client.generate_signed_url(
            key="designs/test.png",
            expiry_hours=24
        )

        # Assert
        mock_s3.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-bucket', 'Key': 'designs/test.png'},
            ExpiresIn=24 * 3600
        )
        assert url == "https://s3.amazonaws.com/test-bucket/designs/test.png?signature=abc123"

    @patch('boto3.client')
    def test_generate_signed_url_with_cdn(self, mock_boto_client):
        """Test signed URL generation with CDN URL replacement."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/designs/test.png?signature=abc123"
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret",
            cdn_url="https://cdn.example.com"
        )

        # Act
        url = client.generate_signed_url(
            key="designs/test.png",
            expiry_hours=24
        )

        # Assert
        assert url.startswith("https://cdn.example.com")
        assert "designs/test.png" in url

    @patch('boto3.client')
    def test_generate_signed_url_error(self, mock_boto_client):
        """Test signed URL generation handles errors."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.side_effect = Exception("S3 error")
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Act & Assert
        with pytest.raises(StorageError, match="Failed to generate signed URL"):
            client.generate_signed_url(key="designs/test.png")

    def test_connection_error_handling(self):
        """Test connection error handling during initialization."""
        # Act & Assert
        with pytest.raises(StorageConnectionError, match="Invalid storage configuration"):
            StorageClient(
                bucket_name="",  # Invalid bucket name
                region="us-east-1",
                access_key="test-key",
                secret_key="test-secret"
            )

    @patch('boto3.client')
    def test_retry_logic_on_failure(self, mock_boto_client):
        """Test retry logic when S3 operations fail temporarily."""
        # Arrange
        mock_s3 = Mock()
        # First call fails, second succeeds
        mock_s3.upload_fileobj.side_effect = [Exception("Temporary failure"), None]
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret",
            max_retries=2
        )
        
        file_obj = io.BytesIO(b"test content")

        # Act
        result = client.upload_file(
            file_obj=file_obj,
            key="designs/test.png",
            content_type="image/png"
        )

        # Assert
        assert mock_s3.upload_fileobj.call_count == 2
        assert result["key"] == "designs/test.png"

    @patch('boto3.client')
    def test_file_exists_check(self, mock_boto_client):
        """Test checking if file exists in storage."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.head_object.return_value = {"ContentLength": 1024}
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Act
        exists = client.file_exists("designs/test.png")

        # Assert
        mock_s3.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="designs/test.png"
        )
        assert exists is True

    @patch('boto3.client')
    def test_file_not_exists(self, mock_boto_client):
        """Test checking non-existent file."""
        # Arrange
        mock_s3 = Mock()
        mock_s3.head_object.side_effect = Exception("Not found")
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Act
        exists = client.file_exists("designs/nonexistent.png")

        # Assert
        assert exists is False

    @patch('boto3.client')
    def test_delete_file_success(self, mock_boto_client):
        """Test successful file deletion."""
        # Arrange
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        client = StorageClient(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret"
        )

        # Act
        result = client.delete_file("designs/test.png")

        # Assert
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="designs/test.png"
        )
        assert result is True