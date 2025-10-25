"""Tests for DesignFile model."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.design import Design
from src.models.design_file import DesignFile


class TestDesignFileModel:
    """Test suite for DesignFile model."""

    def test_create_design_file_with_required_fields(self, db_session):
        """Test creating a DesignFile with all required fields."""
        # Create a design first
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create design file
        design_file = DesignFile(
            design_id=design.id,
            filename="floor_plan.pdf",
            file_type="pdf",
            file_size=1024000,  # 1MB
            storage_path="/storage/designs/1/floor_plan.pdf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        # Verify
        assert design_file.id is not None
        assert design_file.design_id == design.id
        assert design_file.filename == "floor_plan.pdf"
        assert design_file.file_type == "pdf"
        assert design_file.file_size == 1024000
        assert design_file.storage_path == "/storage/designs/1/floor_plan.pdf"
        assert design_file.uploaded_by == 1
        assert design_file.uploaded_at is not None

    def test_create_design_file_with_optional_description(self, db_session):
        """Test creating a DesignFile with optional description."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="elevation.dwg",
            file_type="dwg",
            file_size=5000000,
            storage_path="/storage/designs/1/elevation.dwg",
            uploaded_by=1,
            description="Front elevation drawing"
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.description == "Front elevation drawing"

    def test_file_type_validation_pdf(self, db_session):
        """Test file type validation for PDF files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="document.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="/storage/designs/1/document.pdf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "pdf"

    def test_file_type_validation_dwg(self, db_session):
        """Test file type validation for DWG files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="drawing.dwg",
            file_type="dwg",
            file_size=2000000,
            storage_path="/storage/designs/1/drawing.dwg",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "dwg"

    def test_file_type_validation_dxf(self, db_session):
        """Test file type validation for DXF files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="drawing.dxf",
            file_type="dxf",
            file_size=1500000,
            storage_path="/storage/designs/1/drawing.dxf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "dxf"

    def test_file_type_validation_png(self, db_session):
        """Test file type validation for PNG files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="render.png",
            file_type="png",
            file_size=3000000,
            storage_path="/storage/designs/1/render.png",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "png"

    def test_file_type_validation_jpg(self, db_session):
        """Test file type validation for JPG files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="photo.jpg",
            file_type="jpg",
            file_size=2500000,
            storage_path="/storage/designs/1/photo.jpg",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "jpg"

    def test_file_type_validation_ifc(self, db_session):
        """Test file type validation for IFC files."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="model.ifc",
            file_type="ifc",
            file_size=10000000,
            storage_path="/storage/designs/1/model.ifc",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_type == "ifc"

    def test_file_type_validation_invalid_type(self, db_session):
        """Test that invalid file types raise ValueError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(ValueError, match="File type must be one of"):
            DesignFile(
                design_id=design.id,
                filename="document.txt",
                file_type="txt",
                file_size=1000,
                storage_path="/storage/designs/1/document.txt",
                uploaded_by=1
            )

    def test_file_size_validation_within_limit(self, db_session):
        """Test file size validation for files within 50MB limit."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # 50MB = 52428800 bytes
        design_file = DesignFile(
            design_id=design.id,
            filename="large_file.pdf",
            file_type="pdf",
            file_size=52428800,  # Exactly 50MB
            storage_path="/storage/designs/1/large_file.pdf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        assert design_file.file_size == 52428800

    def test_file_size_validation_exceeds_limit(self, db_session):
        """Test that file size exceeding 50MB raises ValueError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(ValueError, match="File size cannot exceed 50MB"):
            DesignFile(
                design_id=design.id,
                filename="too_large.pdf",
                file_type="pdf",
                file_size=52428801,  # 1 byte over 50MB
                storage_path="/storage/designs/1/too_large.pdf",
                uploaded_by=1
            )

    def test_file_size_validation_negative_size(self, db_session):
        """Test that negative file size raises ValueError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(ValueError, match="File size must be positive"):
            DesignFile(
                design_id=design.id,
                filename="invalid.pdf",
                file_type="pdf",
                file_size=-1000,
                storage_path="/storage/designs/1/invalid.pdf",
                uploaded_by=1
            )

    def test_cascade_delete_with_design(self, db_session):
        """Test that deleting a design cascades to delete its files."""
        # Create design
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create multiple files
        file1 = DesignFile(
            design_id=design.id,
            filename="file1.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="/storage/designs/1/file1.pdf",
            uploaded_by=1
        )
        file2 = DesignFile(
            design_id=design.id,
            filename="file2.dwg",
            file_type="dwg",
            file_size=2000000,
            storage_path="/storage/designs/1/file2.dwg",
            uploaded_by=1
        )
        db_session.add_all([file1, file2])
        db_session.commit()

        file1_id = file1.id
        file2_id = file2.id

        # Delete design
        db_session.delete(design)
        db_session.commit()

        # Verify files are deleted
        assert db_session.get(DesignFile, file1_id) is None
        assert db_session.get(DesignFile, file2_id) is None

    def test_design_relationship(self, db_session):
        """Test the relationship between DesignFile and Design."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="test.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="/storage/designs/1/test.pdf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        # Test relationship from file to design
        assert design_file.design is not None
        assert design_file.design.id == design.id
        assert design_file.design.name == "Test Design"

        # Test relationship from design to files
        assert len(design.files) == 1
        assert design.files[0].id == design_file.id
        assert design.files[0].filename == "test.pdf"

    def test_missing_required_fields(self, db_session):
        """Test that missing required fields raise IntegrityError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Missing filename
        with pytest.raises(IntegrityError):
            design_file = DesignFile(
                design_id=design.id,
                file_type="pdf",
                file_size=1000000,
                storage_path="/storage/designs/1/test.pdf",
                uploaded_by=1
            )
            db_session.add(design_file)
            db_session.commit()

        db_session.rollback()

    def test_repr_method(self, db_session):
        """Test the __repr__ method of DesignFile."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        design_file = DesignFile(
            design_id=design.id,
            filename="test.pdf",
            file_type="pdf",
            file_size=1000000,
            storage_path="/storage/designs/1/test.pdf",
            uploaded_by=1
        )
        db_session.add(design_file)
        db_session.commit()

        repr_str = repr(design_file)
        assert "DesignFile" in repr_str
        assert f"id={design_file.id}" in repr_str
        assert f"design_id={design.id}" in repr_str
        assert "filename='test.pdf'" in repr_str
        assert "file_type='pdf'" in repr_str
