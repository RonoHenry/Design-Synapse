"""Unit tests for DocumentService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from src.api.v1.schemas.document import (CalculationSheetCreateRequest,
                                         CalculationSheetUpdateRequest,
                                         DocumentSearchRequest, DocumentStatus,
                                         DocumentType, SpecificationFormat,
                                         SpecificationGenerateRequest)
from src.models.calculation_sheet import CalculationSheet
from src.services.document_service import DocumentService


class TestDocumentService:
    """Test cases for DocumentService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_calculation_sheet_repo(self):
        """Mock calculation sheet repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def document_service(self, mock_db_session, mock_calculation_sheet_repo):
        """Create DocumentService instance with mocked dependencies."""
        return DocumentService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
        )

    @pytest.fixture
    def sample_calculation_sheet(self):
        """Sample calculation sheet for testing."""
        return CalculationSheet(
            id=1,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            title="Structural Load Calculation",
            description="Load calculation for building",
            calculation_type="structural_loads",
            inputs={"building_height": 20.0, "floor_area": 1000.0},
            outputs={"dead_load": 50.0, "live_load": 40.0, "total_load": 90.0},
            formulas=["Dead Load = Sum of component weights"],
            references=["ASCE 7-16"],
            units="imperial",
            version=1,
            parent_id=None,
            created_by="550e8400-e29b-41d4-a716-446655440001",
            status="draft",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
        )

    @pytest.mark.asyncio
    async def test_create_calculation_sheet(
        self, document_service, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test creating a new calculation sheet."""
        # Arrange
        project_id = uuid4()
        user_id = uuid4()

        request = CalculationSheetCreateRequest(
            project_id=project_id,
            discipline="structural",
            calculation_type="load_calculation",
            inputs={"building_height": 20.0},
            results={"total_load": 100.0},
            formulas={"formulas": ["Load = Weight × Factor"]},
            unit_system="imperial",
        )

        created_sheet = CalculationSheet(
            id=1,
            project_id=str(project_id),
            title="Structural Calculation - Load Calculation",
            calculation_type="load_calculation",
            inputs=request.inputs,
            outputs=request.results,
            formulas=["Load = Weight × Factor"],
            units="imperial",
            version=1,
            created_by=str(user_id),
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_calculation_sheet_repo.create.return_value = created_sheet

        # Act
        result = await document_service.create_calculation_sheet(request, user_id)

        # Assert
        assert result.id == UUID(int=1)
        assert result.project_id == project_id
        assert result.discipline == "structural"
        assert result.calculation_type == "load_calculation"
        assert result.version == 1
        assert result.inputs == request.inputs
        assert result.results == request.results

        mock_calculation_sheet_repo.create.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_calculation_sheet(
        self, document_service, mock_calculation_sheet_repo, sample_calculation_sheet
    ):
        """Test updating a calculation sheet with versioning."""
        # Arrange
        user_id = uuid4()

        request = CalculationSheetUpdateRequest(
            inputs={"building_height": 25.0},  # Updated value
            results={"total_load": 110.0},  # Updated result
        )

        # Mock repository responses
        mock_calculation_sheet_repo.get_by_id.return_value = sample_calculation_sheet
        mock_calculation_sheet_repo.get_latest_version.return_value = (
            sample_calculation_sheet
        )

        new_version = CalculationSheet(
            id=2,
            project_id=sample_calculation_sheet.project_id,
            title=sample_calculation_sheet.title,
            calculation_type=sample_calculation_sheet.calculation_type,
            inputs={"building_height": 25.0, "floor_area": 1000.0},  # Merged inputs
            outputs={
                "dead_load": 50.0,
                "live_load": 40.0,
                "total_load": 110.0,
            },  # Merged outputs
            version=2,
            parent_id=1,  # Points to original
            created_by=str(user_id),
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_calculation_sheet_repo.create.return_value = new_version

        # Act
        result = await document_service.update_calculation_sheet(1, request, user_id)

        # Assert
        assert result.version == 2
        assert result.inputs["building_height"] == 25.0
        assert result.inputs["floor_area"] == 1000.0  # Preserved from original
        assert result.results["total_load"] == 110.0

        mock_calculation_sheet_repo.get_by_id.assert_called_once_with(1)
        mock_calculation_sheet_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_sheet(
        self, document_service, mock_calculation_sheet_repo
    ):
        """Test updating a non-existent calculation sheet."""
        # Arrange
        user_id = uuid4()
        request = CalculationSheetUpdateRequest(inputs={"test": "value"})

        mock_calculation_sheet_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Calculation sheet 999 not found"):
            await document_service.update_calculation_sheet(999, request, user_id)

    @pytest.mark.asyncio
    async def test_get_document_history(
        self, document_service, mock_calculation_sheet_repo, sample_calculation_sheet
    ):
        """Test retrieving document version history."""
        # Arrange
        version_2 = CalculationSheet(
            id=2,
            project_id=sample_calculation_sheet.project_id,
            title=sample_calculation_sheet.title,
            calculation_type=sample_calculation_sheet.calculation_type,
            inputs={"building_height": 25.0, "floor_area": 1000.0},
            outputs={"dead_load": 50.0, "live_load": 40.0, "total_load": 110.0},
            version=2,
            parent_id=1,
            created_by=sample_calculation_sheet.created_by,
            status="approved",
            created_at=datetime(2024, 1, 2, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
        )

        mock_calculation_sheet_repo.get_version_history.return_value = [
            sample_calculation_sheet,
            version_2,
        ]

        # Act
        result = await document_service.get_document_history(1)

        # Assert
        assert result.document_id == UUID(int=1)
        assert result.current_version == 2
        assert len(result.versions) == 2

        # Check first version
        v1 = result.versions[0]
        assert v1.version == 1
        assert v1.changes["action"] == "created"

        # Check second version
        v2 = result.versions[1]
        assert v2.version == 2
        assert v2.changes["action"] == "updated"
        assert "inputs" in v2.changes["fields_changed"]
        assert "outputs" in v2.changes["fields_changed"]
        assert "status" in v2.changes["fields_changed"]

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_document(
        self, document_service, mock_calculation_sheet_repo
    ):
        """Test getting history for non-existent document."""
        # Arrange
        mock_calculation_sheet_repo.get_version_history.return_value = []

        # Act & Assert
        with pytest.raises(ValueError, match="Document 999 not found"):
            await document_service.get_document_history(999)

    @pytest.mark.asyncio
    async def test_generate_csi_masterformat_specification(self, document_service):
        """Test generating CSI MasterFormat specification."""
        # Arrange
        project_id = uuid4()
        design_ids = [uuid4(), uuid4()]

        request = SpecificationGenerateRequest(
            project_id=project_id,
            design_ids=design_ids,
            format=SpecificationFormat.CSI_MASTERFORMAT,
            sections=["03_30_00", "05_12_00"],
        )

        # Act
        result = await document_service.generate_specification(request)

        # Assert
        assert result.project_id == project_id
        assert result.format == SpecificationFormat.CSI_MASTERFORMAT
        assert "03_30_00" in result.sections
        assert "05_12_00" in result.sections

        # Check concrete section
        concrete_section = result.sections["03_30_00"]
        assert concrete_section["title"] == "CAST-IN-PLACE CONCRETE"
        assert concrete_section["section_number"] == "03 30 00"
        assert "part_1_general" in concrete_section
        assert "part_2_products" in concrete_section
        assert "part_3_execution" in concrete_section

        # Check steel section
        steel_section = result.sections["05_12_00"]
        assert steel_section["title"] == "STRUCTURAL STEEL FRAMING"
        assert steel_section["section_number"] == "05 12 00"

    @pytest.mark.asyncio
    async def test_generate_uniformat_specification(self, document_service):
        """Test generating UNIFORMAT specification."""
        # Arrange
        project_id = uuid4()
        design_ids = [uuid4()]

        request = SpecificationGenerateRequest(
            project_id=project_id,
            design_ids=design_ids,
            format=SpecificationFormat.UNIFORMAT,
            sections=["A10", "B20"],
        )

        # Act
        result = await document_service.generate_specification(request)

        # Assert
        assert result.format == SpecificationFormat.UNIFORMAT
        assert "A10" in result.sections
        assert "B20" in result.sections

        # Check UNIFORMAT format
        section = result.sections["A10"]
        assert "UNIFORMAT Section A10" in section["title"]

    @pytest.mark.asyncio
    async def test_search_documents_by_project(
        self, document_service, mock_db_session, sample_calculation_sheet
    ):
        """Test searching documents by project ID."""
        # Arrange
        project_id = uuid4()

        request = DocumentSearchRequest(
            project_id=project_id,
        )

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_calculation_sheet]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await document_service.search_documents(request)

        # Assert
        assert result.total_count == 1
        assert len(result.documents) == 1
        assert result.documents[0].id == UUID(int=1)

        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_by_discipline(
        self, document_service, mock_db_session, sample_calculation_sheet
    ):
        """Test searching documents by discipline."""
        # Arrange
        request = DocumentSearchRequest(
            discipline="structural",
        )

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_calculation_sheet]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await document_service.search_documents(request)

        # Assert
        assert result.total_count == 1
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_search_documents_by_text(
        self, document_service, mock_db_session, sample_calculation_sheet
    ):
        """Test searching documents by text."""
        # Arrange
        request = DocumentSearchRequest(
            search_text="load",
        )

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_calculation_sheet]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await document_service.search_documents(request)

        # Assert
        assert result.total_count == 1
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_search_documents_by_status(
        self, document_service, mock_db_session, sample_calculation_sheet
    ):
        """Test searching documents by status."""
        # Arrange
        request = DocumentSearchRequest(
            status=DocumentStatus.DRAFT,
        )

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_calculation_sheet]
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await document_service.search_documents(request)

        # Assert
        assert result.total_count == 1
        assert len(result.documents) == 1

    @pytest.mark.asyncio
    async def test_search_documents_no_results(self, document_service, mock_db_session):
        """Test searching documents with no results."""
        # Arrange
        request = DocumentSearchRequest(
            search_text="nonexistent",
        )

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Act
        result = await document_service.search_documents(request)

        # Assert
        assert result.total_count == 0
        assert len(result.documents) == 0

    def test_extract_discipline(self, document_service):
        """Test discipline extraction from calculation type."""
        # Test structural
        assert document_service._extract_discipline("structural_loads") == "structural"
        assert document_service._extract_discipline("beam_design") == "structural"

        # Test MEP
        assert document_service._extract_discipline("hvac_design") == "mep"
        assert document_service._extract_discipline("electrical_load") == "mep"
        assert document_service._extract_discipline("plumbing_sizing") == "mep"
        assert document_service._extract_discipline("fire_protection") == "mep"

        # Test civil
        assert document_service._extract_discipline("civil_grading") == "civil"

        # Test general
        assert document_service._extract_discipline("unknown_type") == "general"

    def test_calculate_changes(self, document_service, sample_calculation_sheet):
        """Test change calculation between versions."""
        # Create modified version
        modified_sheet = CalculationSheet(
            id=2,
            project_id=sample_calculation_sheet.project_id,
            title=sample_calculation_sheet.title,
            calculation_type=sample_calculation_sheet.calculation_type,
            inputs={"building_height": 25.0, "floor_area": 1000.0},  # Changed height
            outputs={
                "dead_load": 55.0,
                "live_load": 40.0,
                "total_load": 95.0,
            },  # Changed dead load
            version=2,
            parent_id=1,
            created_by=sample_calculation_sheet.created_by,
            status="approved",  # Changed status
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        changes = document_service._calculate_changes(
            sample_calculation_sheet, modified_sheet
        )

        # Assert
        assert changes["action"] == "updated"
        assert "inputs" in changes["fields_changed"]
        assert "outputs" in changes["fields_changed"]
        assert "status" in changes["fields_changed"]

        # Check input changes
        input_summary = changes["inputs_summary"]
        assert "building_height" in input_summary["modified"]

        # Check output changes
        output_summary = changes["outputs_summary"]
        assert "dead_load" in output_summary["modified"]
        assert "total_load" in output_summary["modified"]

        # Check status change
        status_change = changes["status_change"]
        assert status_change["from"] == "draft"
        assert status_change["to"] == "approved"

    def test_summarize_dict_changes(self, document_service):
        """Test dictionary change summarization."""
        old_dict = {"a": 1, "b": 2, "c": 3}
        new_dict = {"a": 1, "b": 20, "d": 4}  # b modified, c removed, d added

        summary = document_service._summarize_dict_changes(old_dict, new_dict)

        assert summary["added"] == ["d"]
        assert summary["modified"] == ["b"]
        assert summary["removed"] == ["c"]

    def test_to_response_conversion(self, document_service, sample_calculation_sheet):
        """Test conversion from model to response schema."""
        response = document_service._to_response(sample_calculation_sheet)

        assert response.id == UUID(int=1)
        assert str(response.project_id) == sample_calculation_sheet.project_id
        assert response.discipline == "structural"
        assert response.calculation_type == sample_calculation_sheet.calculation_type
        assert response.version == sample_calculation_sheet.version
        assert response.inputs == sample_calculation_sheet.inputs
        assert response.results == sample_calculation_sheet.outputs
        assert response.unit_system == sample_calculation_sheet.units
