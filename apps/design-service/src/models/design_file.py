"""DesignFile model for files attached to designs."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


class DesignFile(Base):
    """Files attached to designs (CAD, images, PDFs).
    
    Supports common design file formats with size validation
    and CASCADE delete when parent design is removed.
    """
    __tablename__ = "design_files"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign key to Design
    design_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    uploaded_by: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="files"
    )

    # Allowed file types
    ALLOWED_FILE_TYPES = ["pdf", "dwg", "dxf", "png", "jpg", "ifc"]
    
    # Maximum file size (50MB in bytes)
    MAX_FILE_SIZE = 52428800  # 50 * 1024 * 1024

    def __init__(
        self,
        design_id: Optional[int] = None,
        filename: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        storage_path: Optional[str] = None,
        uploaded_by: Optional[int] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize a new design file.

        Args:
            design_id: ID of the design this file belongs to
            filename: Name of the file
            file_type: Type of file (pdf, dwg, dxf, png, jpg, ifc)
            file_size: Size of file in bytes
            storage_path: Path where file is stored
            uploaded_by: ID of the user who uploaded the file
            description: Optional description of the file

        Raises:
            ValueError: If validation fails
        """
        # Validate file type
        if file_type is not None:
            if file_type.lower() not in self.ALLOWED_FILE_TYPES:
                raise ValueError(
                    f"File type must be one of: {', '.join(self.ALLOWED_FILE_TYPES)}"
                )
            file_type = file_type.lower()

        # Validate file size
        if file_size is not None:
            if file_size < 0:
                raise ValueError("File size must be positive")
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"File size cannot exceed 50MB ({self.MAX_FILE_SIZE} bytes)"
                )

        # Set fields (SQLAlchemy will enforce NOT NULL constraints at commit time)
        if design_id is not None:
            self.design_id = design_id
        if filename is not None:
            self.filename = filename
        if file_type is not None:
            self.file_type = file_type
        if file_size is not None:
            self.file_size = file_size
        if storage_path is not None:
            self.storage_path = storage_path
        if uploaded_by is not None:
            self.uploaded_by = uploaded_by
        
        self.description = description
        self.uploaded_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """String representation of DesignFile."""
        return (
            f"<DesignFile(id={self.id}, "
            f"design_id={self.design_id}, "
            f"filename='{self.filename}', "
            f"file_type='{self.file_type}')>"
        )
