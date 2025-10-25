"""
File management API routes.

This module provides REST API endpoints for:
- Uploading files to designs
- Listing files attached to designs
- Deleting files
- Downloading files
"""

import os
import shutil
from pathlib import Path
from typing import List
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ....infrastructure.database import get_db
from ....repositories.design_repository import DesignRepository
from ....services.project_client import ProjectClient, ProjectAccessDeniedError
from ....models.design_file import DesignFile
from ...dependencies import CurrentUserId, get_current_user_id
from ..schemas.responses import DesignFileResponse

router = APIRouter(tags=["files"])


def get_design_repository(db: Session = Depends(get_db)) -> DesignRepository:
    """Dependency to get design repository instance."""
    return DesignRepository(db)


def get_project_client() -> ProjectClient:
    """Dependency to get project client instance."""
    return ProjectClient()


def get_storage_path() -> Path:
    """Get the base storage path for design files."""
    from ....core.config import get_settings
    
    # Get storage path from config or use default
    storage_path = os.getenv("FILE_STORAGE_PATH", "./storage/designs")
    path = Path(storage_path)
    
    # Create directory if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)
    
    return path


def validate_file_type(filename: str) -> str:
    """
    Validate and extract file type from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension in lowercase
        
    Raises:
        HTTPException: If file type is not supported
    """
    # Extract file extension
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    # Check if file type is allowed
    if file_ext not in DesignFile.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(DesignFile.ALLOWED_FILE_TYPES)}",
        )
    
    return file_ext


def validate_file_size(file_size: int) -> None:
    """
    Validate file size.
    
    Args:
        file_size: Size of file in bytes
        
    Raises:
        HTTPException: If file size exceeds limit
    """
    if file_size > DesignFile.MAX_FILE_SIZE:
        max_mb = DesignFile.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {max_mb:.0f}MB",
        )


async def save_upload_file(
    upload_file: UploadFile,
    destination: Path,
) -> int:
    """
    Save uploaded file to destination and return file size.
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Path where file should be saved
        
    Returns:
        Size of saved file in bytes
        
    Raises:
        HTTPException: If file save fails
    """
    try:
        # Ensure parent directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Save file in chunks to handle large files
        file_size = 0
        with open(destination, "wb") as buffer:
            while chunk := await upload_file.read(8192):  # 8KB chunks
                file_size += len(chunk)
                
                # Check size limit during upload
                if file_size > DesignFile.MAX_FILE_SIZE:
                    # Clean up partial file
                    buffer.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File size exceeds maximum limit of 50MB",
                    )
                
                buffer.write(chunk)
        
        return file_size
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )


@router.post(
    "/designs/{design_id}/files",
    response_model=DesignFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to a design",
    description="Upload a file (PDF, DWG, DXF, PNG, JPG, IFC) to a design. Max size: 50MB",
)
async def upload_file(
    design_id: int,
    user_id: CurrentUserId,
    file: UploadFile = File(..., description="File to upload"),
    description: str = Form(None, description="Optional file description"),
    db: Session = Depends(get_db),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
    storage_path: Path = Depends(get_storage_path),
) -> DesignFileResponse:
    """
    Upload a file to a design.
    
    Args:
        design_id: ID of the design to attach file to
        file: File to upload
        description: Optional description of the file
        user_id: Current authenticated user ID
        db: Database session
        repository: Design repository
        project_client: Project service client
        storage_path: Base storage path
        
    Returns:
        Created file metadata
        
    Raises:
        400: If file type is unsupported or size exceeds limit
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Validate file type
    file_type = validate_file_type(file.filename)
    
    # Generate unique filename to avoid collisions
    import uuid
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = storage_path / str(design_id) / unique_filename
    
    # Save file and get size
    file_size = await save_upload_file(file, file_path)
    
    # Create database record
    try:
        design_file = DesignFile(
            design_id=design_id,
            filename=file.filename,  # Store original filename
            file_type=file_type,
            file_size=file_size,
            storage_path=str(file_path),
            uploaded_by=user_id,
            description=description,
        )
        
        db.add(design_file)
        db.commit()
        db.refresh(design_file)
        
        return DesignFileResponse.model_validate(design_file)
        
    except Exception as e:
        # Clean up file on database error
        file_path.unlink(missing_ok=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file metadata: {str(e)}",
        )


@router.get(
    "/designs/{design_id}/files",
    response_model=List[DesignFileResponse],
    summary="List files for a design",
    description="Get all files attached to a design",
)
async def list_files(
    design_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> List[DesignFileResponse]:
    """
    List all files attached to a design.
    
    Args:
        design_id: ID of the design
        user_id: Current authenticated user ID
        db: Database session
        repository: Design repository
        project_client: Project service client
        
    Returns:
        List of file metadata
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If design not found
    """
    # Get design
    design = repository.get_design_by_id(design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Get files
    files = db.query(DesignFile).filter(
        DesignFile.design_id == design_id
    ).order_by(DesignFile.uploaded_at.desc()).all()
    
    return [DesignFileResponse.model_validate(f) for f in files]


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file from a design",
)
async def delete_file(
    file_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
) -> None:
    """
    Delete a file.
    
    Args:
        file_id: ID of the file to delete
        user_id: Current authenticated user ID
        db: Database session
        repository: Design repository
        project_client: Project service client
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If file not found
    """
    # Get file
    design_file = db.query(DesignFile).filter(DesignFile.id == file_id).first()
    
    if not design_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )
    
    # Get design to verify project access
    design = repository.get_design_by_id(design_file.design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_file.design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Delete file from storage
    try:
        file_path = Path(design_file.storage_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Warning: Failed to delete file from storage: {e}")
    
    # Delete from database
    db.delete(design_file)
    db.commit()


@router.get(
    "/files/{file_id}/download",
    summary="Download a file",
    description="Download a file from a design",
)
async def download_file(
    file_id: int,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
):
    """
    Download a file.
    
    Args:
        file_id: ID of the file to download
        user_id: Current authenticated user ID
        db: Database session
        repository: Design repository
        project_client: Project service client
        
    Returns:
        File content as streaming response
        
    Raises:
        401: If authentication fails
        403: If user doesn't have access to the project
        404: If file not found or storage file missing
    """
    # Get file
    design_file = db.query(DesignFile).filter(DesignFile.id == file_id).first()
    
    if not design_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found",
        )
    
    # Get design to verify project access
    design = repository.get_design_by_id(design_file.design_id, include_archived=False)
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_file.design_id} not found",
        )
    
    # Verify project access
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    # Check if file exists in storage
    file_path = Path(design_file.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage",
        )
    
    # Determine media type based on file extension
    media_types = {
        "pdf": "application/pdf",
        "dwg": "application/acad",
        "dxf": "application/dxf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "ifc": "application/x-step",
    }
    media_type = media_types.get(design_file.file_type, "application/octet-stream")
    
    # Return file as streaming response for large files
    def iterfile():
        """Generator to stream file in chunks."""
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # 8KB chunks
                yield chunk
    
    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{design_file.filename}"',
            "Content-Length": str(design_file.file_size),
        },
    )
