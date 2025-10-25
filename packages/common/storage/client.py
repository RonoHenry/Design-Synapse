"""
Storage client for file upload and management.

Provides a unified interface for cloud storage operations
with S3 integration, retry logic, and error handling.
"""

import io
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.exceptions import ClientError


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""
    pass


class StorageClient:
    """Client for cloud storage operations."""

    def __init__(
        self,
        bucket_name: str,
        region: str,
        access_key: str,
        secret_key: str,
        cdn_url: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Initialize storage client.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key: AWS access key
            secret_key: AWS secret key
            cdn_url: Optional CDN URL for serving files
            max_retries: Maximum retry attempts for failed operations

        Raises:
            StorageConnectionError: If configuration is invalid
        """
        # Validate configuration
        if not bucket_name or not bucket_name.strip():
            raise StorageConnectionError("Invalid storage configuration: bucket_name cannot be empty")
        if not region or not region.strip():
            raise StorageConnectionError("Invalid storage configuration: region cannot be empty")
        if not access_key or not access_key.strip():
            raise StorageConnectionError("Invalid storage configuration: access_key cannot be empty")
        if not secret_key or not secret_key.strip():
            raise StorageConnectionError("Invalid storage configuration: secret_key cannot be empty")

        self.bucket_name = bucket_name
        self.region = region
        self._access_key = access_key
        self._secret_key = secret_key
        self.cdn_url = cdn_url
        self.max_retries = max_retries

        # Initialize S3 client
        self._s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

    def upload_file(
        self,
        file_obj: io.IOBase,
        key: str,
        content_type: str,
        compress: bool = False
    ) -> Dict[str, Any]:
        """
        Upload file to storage.

        Args:
            file_obj: File-like object to upload
            key: Storage key/path for the file
            content_type: MIME type of the file
            compress: Whether to compress the file

        Returns:
            Dictionary with upload result information

        Raises:
            StorageError: If upload fails
        """
        original_size = self._get_file_size(file_obj)
        
        # Handle compression if requested
        if compress and content_type.startswith('image/'):
            compressed_content = self._compress_image(file_obj)
            compressed_size = len(compressed_content)
            upload_obj = io.BytesIO(compressed_content)
        else:
            upload_obj = file_obj
            compressed_size = original_size

        # Upload with retry logic
        for attempt in range(self.max_retries):
            try:
                self._s3_client.upload_fileobj(
                    upload_obj,
                    self.bucket_name,
                    key,
                    ExtraArgs={'ContentType': content_type}
                )
                
                # Generate URL
                url = self._generate_public_url(key)
                
                result = {
                    "key": key,
                    "bucket": self.bucket_name,
                    "url": url,
                    "size": compressed_size,
                    "content_type": content_type
                }
                
                if compress and content_type.startswith('image/'):
                    result.update({
                        "compressed": True,
                        "original_size": original_size,
                        "compressed_size": compressed_size
                    })
                
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise StorageError(f"Failed to upload file: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def generate_signed_url(
        self,
        key: str,
        expiry_hours: int = 24
    ) -> str:
        """
        Generate signed URL for file access.

        Args:
            key: Storage key/path for the file
            expiry_hours: URL expiry time in hours

        Returns:
            Signed URL string

        Raises:
            StorageError: If URL generation fails
        """
        try:
            url = self._s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiry_hours * 3600
            )
            
            # Replace with CDN URL if configured
            if self.cdn_url:
                parsed_url = urlparse(url)
                cdn_parsed = urlparse(self.cdn_url)
                new_url = urlunparse((
                    cdn_parsed.scheme,
                    cdn_parsed.netloc,
                    f"/{key}",
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment
                ))
                return new_url
            
            return url
            
        except Exception as e:
            raise StorageError(f"Failed to generate signed URL: {e}")

    def file_exists(self, key: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            key: Storage key/path for the file

        Returns:
            True if file exists, False otherwise
        """
        try:
            self._s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def delete_file(self, key: str) -> bool:
        """
        Delete file from storage.

        Args:
            key: Storage key/path for the file

        Returns:
            True if deletion successful

        Raises:
            StorageError: If deletion fails
        """
        try:
            self._s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete file: {e}")

    def _get_file_size(self, file_obj: io.IOBase) -> int:
        """Get size of file object."""
        current_pos = file_obj.tell()
        file_obj.seek(0, 2)  # Seek to end
        size = file_obj.tell()
        file_obj.seek(current_pos)  # Restore position
        return size

    def _compress_image(self, file_obj: io.IOBase) -> bytes:
        """Compress image file using Pillow."""
        try:
            from PIL import Image
            
            # Read image
            content = file_obj.read()
            file_obj.seek(0)  # Reset position
            
            # Open with Pillow
            image = Image.open(io.BytesIO(content))
            
            # Compress and save
            output = io.BytesIO()
            # Reduce quality for compression
            image.save(output, format=image.format, quality=85, optimize=True)
            
            return output.getvalue()
            
        except ImportError:
            # Fallback if Pillow not available
            content = file_obj.read()
            file_obj.seek(0)
            return content
        except Exception:
            # Fallback on any compression error
            content = file_obj.read()
            file_obj.seek(0)
            return content

    def _generate_public_url(self, key: str) -> str:
        """Generate public URL for file."""
        if self.cdn_url:
            return f"{self.cdn_url.rstrip('/')}/{key}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"