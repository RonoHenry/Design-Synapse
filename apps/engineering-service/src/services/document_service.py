"""
Document Management Service for engineering documents.

This service handles creation, versioning, search, and specification generation
for engineering documents including calculation sheets and technical specifications.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.v1.schemas.document import (CalculationSheetCreateRequest,
                                       CalculationSheetResponse,
                                       CalculationSheetUpdateRequest,
                                       DocumentHistoryResponse,
                                       DocumentSearchRequest,
                                       DocumentSearchResponse,
                                       DocumentVersionSchema,
                                       SpecificationFormat,
                                       SpecificationGenerateRequest,
                                       SpecificationResponse)
from ..models.calculation_sheet import CalculationSheet
from ..repositories.calculation_sheet_repository import \
    CalculationSheetRepository


class DocumentService:
    """
    Service for managing engineering documents.

    Provides document lifecycle management including:
    - Creation with versioning
    - Updates with version control
    - History tracking
    - Search functionality
    - CSI MasterFormat specification generation
    """

    def __init__(
        self,
        db_session: AsyncSession,
        calculation_sheet_repo: Optional[CalculationSheetRepository] = None,
    ):
        """
        Initialize the document service.

        Args:
            db_session: Database session for persistence
            calculation_sheet_repo: Repository for calculation sheets
        """
        self.db_session = db_session
        self.calculation_sheet_repo = (
            calculation_sheet_repo or CalculationSheetRepository(db_session)
        )

    async def create_calculation_sheet(
        self,
        request: CalculationSheetCreateRequest,
        user_id: UUID,
    ) -> CalculationSheetResponse:
        """
        Create a new versioned calculation sheet.

        Associates the sheet with the specified project and discipline,
        and initializes version control.

        Args:
            request: Calculation sheet creation request
            user_id: User creating the sheet

        Returns:
            Created calculation sheet response

        Requirements: 4.1, 4.5
        """
        # Create calculation sheet with version 1
        calculation_sheet = CalculationSheet(
            project_id=str(request.project_id),
            title=f"{request.discipline.title()} Calculation - "
            f"{request.calculation_type.replace('_', ' ').title()}",
            description=f"{request.discipline} calculation sheet for "
            f"{request.calculation_type}",
            calculation_type=request.calculation_type,
            inputs=request.inputs,
            outputs=request.results,
            formulas=request.formulas.get("formulas", [])
            if isinstance(request.formulas, dict)
            else [],
            references=request.formulas.get("references", [])
            if isinstance(request.formulas, dict)
            else [],
            units=request.unit_system,
            version=1,
            parent_id=None,  # This is the original version
            created_by=str(user_id),
            status="draft",
        )

        # Save to database
        saved_sheet = await self.calculation_sheet_repo.create(calculation_sheet)
        await self.db_session.commit()

        return self._to_response(saved_sheet)

    async def update_calculation_sheet(
        self,
        sheet_id: int,
        request: CalculationSheetUpdateRequest,
        user_id: UUID,
    ) -> CalculationSheetResponse:
        """
        Update calculation sheet with versioning.

        Creates a new version on updates while preserving previous versions.
        The original sheet becomes the parent for version tracking.

        Args:
            sheet_id: ID of the calculation sheet to update
            request: Update request with new values
            user_id: User performing the update

        Returns:
            Updated calculation sheet response

        Requirements: 4.2
        """
        # Get the current sheet
        current_sheet = await self.calculation_sheet_repo.get_by_id(sheet_id)
        if not current_sheet:
            raise ValueError(f"Calculation sheet {sheet_id} not found")

        # Get the latest version to determine next version number
        latest_sheet = await self.calculation_sheet_repo.get_latest_version(sheet_id)
        if not latest_sheet:
            latest_sheet = current_sheet

        next_version = latest_sheet.version + 1

        # Determine the parent ID (original sheet ID)
        parent_id = current_sheet.parent_id or current_sheet.id

        # Create new version with updated data
        new_inputs = current_sheet.inputs.copy()
        if request.inputs:
            new_inputs.update(request.inputs)

        new_outputs = current_sheet.outputs.copy()
        if request.results:
            new_outputs.update(request.results)

        new_formulas = current_sheet.formulas.copy() if current_sheet.formulas else []
        if request.formulas:
            if isinstance(request.formulas, dict):
                new_formulas = request.formulas.get("formulas", new_formulas)
            else:
                new_formulas = request.formulas

        # Create new version
        new_version = CalculationSheet(
            project_id=current_sheet.project_id,
            title=current_sheet.title,
            description=current_sheet.description,
            calculation_type=current_sheet.calculation_type,
            inputs=new_inputs,
            outputs=new_outputs,
            formulas=new_formulas,
            references=current_sheet.references,
            units=current_sheet.units,
            version=next_version,
            parent_id=parent_id,
            created_by=str(user_id),
            status="draft",
        )

        # Save new version
        saved_version = await self.calculation_sheet_repo.create(new_version)
        await self.db_session.commit()

        return self._to_response(saved_version)

    async def get_document_history(
        self,
        document_id: int,
    ) -> DocumentHistoryResponse:
        """
        Return all versions with change summaries.

        Retrieves the complete version history for a document,
        including details about what changed in each version.

        Args:
            document_id: ID of the document

        Returns:
            Document history with all versions

        Requirements: 4.3
        """
        # Get all versions of the document
        versions = await self.calculation_sheet_repo.get_version_history(document_id)

        if not versions:
            raise ValueError(f"Document {document_id} not found")

        # Get the current version number
        current_version = max(v.version for v in versions)

        # Build version history with change summaries
        version_schemas = []
        for i, version in enumerate(versions):
            changes = {}

            if i > 0:  # Compare with previous version
                prev_version = versions[i - 1]
                changes = self._calculate_changes(prev_version, version)
            else:
                changes = {"action": "created", "summary": "Initial version"}

            version_schema = DocumentVersionSchema(
                version=version.version,
                changes=changes,
                updated_by=UUID(version.created_by),
                updated_at=version.created_at,
            )
            version_schemas.append(version_schema)

        return DocumentHistoryResponse(
            document_id=UUID(int=document_id),  # Convert int to UUID for response
            current_version=current_version,
            versions=version_schemas,
        )

    async def generate_specification(
        self,
        request: SpecificationGenerateRequest,
    ) -> SpecificationResponse:
        """
        Generate CSI MasterFormat specification.

        Formats specifications according to CSI MasterFormat standards
        based on the provided design data and sections.

        Args:
            request: Specification generation request

        Returns:
            Generated specification response

        Requirements: 4.4
        """
        # Get design data for the specified design IDs
        design_data = await self._get_design_data(request.design_ids)

        # Generate specification based on format
        if request.format == SpecificationFormat.CSI_MASTERFORMAT:
            sections = self._generate_csi_masterformat(design_data, request.sections)
        else:
            sections = self._generate_uniformat(design_data, request.sections)

        # Create specification response
        spec_id = uuid4()

        return SpecificationResponse(
            specification_id=spec_id,
            project_id=request.project_id,
            format=request.format,
            sections=sections,
            generated_at=datetime.utcnow(),
        )

    async def search_documents(
        self,
        request: DocumentSearchRequest,
    ) -> DocumentSearchResponse:
        """
        Search documents with filtering.

        Returns results filtered by project, discipline, document type,
        and date range as specified in the search request.

        Args:
            request: Document search request

        Returns:
            Search results with matching documents

        Requirements: 4.6
        """
        # Build query conditions
        conditions = []

        if request.project_id:
            conditions.append(CalculationSheet.project_id == str(request.project_id))

        if request.discipline:
            # Search in calculation_type field for discipline
            conditions.append(
                CalculationSheet.calculation_type.ilike(f"%{request.discipline}%")
            )

        if request.search_text:
            # Search in title and description
            text_condition = or_(
                CalculationSheet.title.ilike(f"%{request.search_text}%"),
                CalculationSheet.description.ilike(f"%{request.search_text}%"),
            )
            conditions.append(text_condition)

        if request.status:
            status_value = (
                request.status.value
                if hasattr(request.status, "value")
                else request.status
            )
            conditions.append(CalculationSheet.status == status_value)

        # Execute search query
        query = select(CalculationSheet)

        if conditions:
            query = query.where(and_(*conditions))

        # Exclude soft-deleted records
        query = query.where(CalculationSheet.deleted_at.is_(None))

        # Order by creation date (newest first)
        query = query.order_by(CalculationSheet.created_at.desc())

        result = await self.db_session.execute(query)
        sheets = list(result.scalars().all())

        # Convert to response format
        documents = [self._to_response(sheet) for sheet in sheets]

        return DocumentSearchResponse(
            total_count=len(documents),
            documents=documents,
        )

    def _to_response(self, sheet: CalculationSheet) -> CalculationSheetResponse:
        """Convert CalculationSheet model to response schema."""
        return CalculationSheetResponse(
            id=UUID(int=sheet.id),  # Convert int to UUID for response
            project_id=UUID(sheet.project_id),
            discipline=self._extract_discipline(sheet.calculation_type),
            calculation_type=sheet.calculation_type,
            version=sheet.version,
            inputs=sheet.inputs,
            results=sheet.outputs,
            formulas={
                "formulas": sheet.formulas or [],
                "references": sheet.references or [],
            },
            unit_system=sheet.units or "imperial",
            created_by=UUID(sheet.created_by),
            created_at=sheet.created_at,
            updated_at=sheet.updated_at,
        )

    def _extract_discipline(self, calculation_type: str) -> str:
        """Extract discipline from calculation type."""
        calc_type_lower = calculation_type.lower()

        # Check MEP first (more specific terms)
        if "mep" in calc_type_lower or any(
            term in calc_type_lower
            for term in ["hvac", "electrical", "plumbing", "fire"]
        ):
            return "mep"
        # Check civil next
        elif "civil" in calc_type_lower or any(
            term in calc_type_lower
            for term in ["grading", "stormwater", "utility", "site"]
        ):
            return "civil"
        # Check structural last (to avoid conflicts with "load" in electrical_load)
        elif "structural" in calc_type_lower or any(
            term in calc_type_lower
            for term in ["beam", "column", "foundation"]
            + (
                ["load"]
                if not any(
                    mep_term in calc_type_lower
                    for mep_term in ["electrical", "hvac", "plumbing"]
                )
                else []
            )
        ):
            return "structural"
        else:
            return "general"

    def _calculate_changes(
        self, prev_version: CalculationSheet, current_version: CalculationSheet
    ) -> Dict[str, Any]:
        """Calculate changes between two versions."""
        changes = {"action": "updated", "fields_changed": []}

        # Check inputs
        if prev_version.inputs != current_version.inputs:
            changes["fields_changed"].append("inputs")
            changes["inputs_summary"] = self._summarize_dict_changes(
                prev_version.inputs, current_version.inputs
            )

        # Check outputs
        if prev_version.outputs != current_version.outputs:
            changes["fields_changed"].append("outputs")
            changes["outputs_summary"] = self._summarize_dict_changes(
                prev_version.outputs, current_version.outputs
            )

        # Check formulas
        if prev_version.formulas != current_version.formulas:
            changes["fields_changed"].append("formulas")

        # Check status
        if prev_version.status != current_version.status:
            changes["fields_changed"].append("status")
            changes["status_change"] = {
                "from": prev_version.status,
                "to": current_version.status,
            }

        if not changes["fields_changed"]:
            changes["summary"] = "No significant changes"
        else:
            changes["summary"] = f"Updated: {', '.join(changes['fields_changed'])}"

        return changes

    def _summarize_dict_changes(
        self, old_dict: Dict[str, Any], new_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Summarize changes between two dictionaries."""
        summary = {
            "added": [],
            "modified": [],
            "removed": [],
        }

        old_keys = set(old_dict.keys())
        new_keys = set(new_dict.keys())

        # Added keys
        summary["added"] = list(new_keys - old_keys)

        # Removed keys
        summary["removed"] = list(old_keys - new_keys)

        # Modified keys
        for key in old_keys & new_keys:
            if old_dict[key] != new_dict[key]:
                summary["modified"].append(key)

        return summary

    async def _get_design_data(self, design_ids: List[UUID]) -> List[Dict[str, Any]]:
        """Get design data for specification generation."""
        # For now, return mock data since we don't have design service integration
        # In a real implementation, this would call the design service
        design_data = []

        for design_id in design_ids:
            # Mock design data
            design_data.append(
                {
                    "id": str(design_id),
                    "type": "structural",
                    "materials": ["Steel", "Concrete"],
                    "specifications": {
                        "steel_grade": "A992",
                        "concrete_strength": "4000 psi",
                    },
                }
            )

        return design_data

    def _generate_csi_masterformat(
        self, design_data: List[Dict[str, Any]], sections: List[str]
    ) -> Dict[str, Any]:
        """Generate CSI MasterFormat specification sections."""
        spec_sections = {}

        for section in sections:
            if section == "03_30_00":  # Cast-in-Place Concrete
                spec_sections[section] = self._generate_concrete_section(design_data)
            elif section == "05_12_00":  # Structural Steel Framing
                spec_sections[section] = self._generate_steel_section(design_data)
            elif section == "23_00_00":  # HVAC
                spec_sections[section] = self._generate_hvac_section(design_data)
            elif section == "26_00_00":  # Electrical
                spec_sections[section] = self._generate_electrical_section(design_data)
            else:
                # Generic section
                spec_sections[section] = self._generate_generic_section(
                    section, design_data
                )

        return spec_sections

    def _generate_uniformat(
        self, design_data: List[Dict[str, Any]], sections: List[str]
    ) -> Dict[str, Any]:
        """Generate UNIFORMAT specification sections."""
        spec_sections = {}

        for section in sections:
            spec_sections[section] = {
                "title": f"UNIFORMAT Section {section}",
                "description": "UNIFORMAT specification section",
                "requirements": ["To be developed based on design data"],
            }

        return spec_sections

    def _generate_concrete_section(
        self, design_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate concrete specification section."""
        return {
            "title": "CAST-IN-PLACE CONCRETE",
            "section_number": "03 30 00",
            "part_1_general": {
                "summary": "This section covers cast-in-place concrete for structural elements.",
                "references": [
                    "ACI 301 - Specifications for Structural Concrete",
                    "ACI 318 - Building Code Requirements for Structural Concrete",
                ],
                "submittals": [
                    "Mix designs",
                    "Material certificates",
                    "Test reports",
                ],
            },
            "part_2_products": {
                "concrete_materials": {
                    "cement": "Portland cement conforming to ASTM C150",
                    "aggregates": "Conforming to ASTM C33",
                    "water": "Potable water",
                },
                "concrete_mixes": [
                    {
                        "strength": "4000 psi at 28 days",
                        "slump": "4 inches maximum",
                        "air_content": "6% ± 1%",
                    }
                ],
            },
            "part_3_execution": {
                "placement": "Place concrete in accordance with ACI 301",
                "curing": "Moist cure for minimum 7 days",
                "testing": "Test in accordance with ASTM C39",
            },
        }

    def _generate_steel_section(
        self, design_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate structural steel specification section."""
        return {
            "title": "STRUCTURAL STEEL FRAMING",
            "section_number": "05 12 00",
            "part_1_general": {
                "summary": "This section covers structural steel framing.",
                "references": [
                    "AISC 360 - Specification for Structural Steel Buildings",
                    "AWS D1.1 - Structural Welding Code",
                ],
            },
            "part_2_products": {
                "steel_materials": {
                    "structural_steel": "ASTM A992 Grade 50",
                    "bolts": "ASTM A325 high-strength bolts",
                    "welding_electrodes": "AWS E70XX",
                },
            },
            "part_3_execution": {
                "fabrication": "Shop fabricate in accordance with AISC 303",
                "erection": "Erect in accordance with AISC 303",
                "welding": "Weld in accordance with AWS D1.1",
            },
        }

    def _generate_hvac_section(
        self, design_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate HVAC specification section."""
        return {
            "title": "HVAC SYSTEMS",
            "section_number": "23 00 00",
            "part_1_general": {
                "summary": "This section covers HVAC systems and equipment.",
                "references": [
                    "ASHRAE 90.1 - Energy Standard for Buildings",
                    "SMACNA - Sheet Metal and Air Conditioning Contractors",
                ],
            },
            "part_2_products": {
                "equipment": "Factory-assembled units",
                "ductwork": "Galvanized steel conforming to SMACNA standards",
                "controls": "Direct digital control system",
            },
            "part_3_execution": {
                "installation": "Install in accordance with manufacturer instructions",
                "testing": "Test and balance entire system",
                "commissioning": "Commission all systems per ASHRAE Guideline 1",
            },
        }

    def _generate_electrical_section(
        self, design_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate electrical specification section."""
        return {
            "title": "ELECTRICAL SYSTEMS",
            "section_number": "26 00 00",
            "part_1_general": {
                "summary": "This section covers electrical systems and equipment.",
                "references": [
                    "NEC - National Electrical Code",
                    "UL - Underwriters Laboratories Standards",
                ],
            },
            "part_2_products": {
                "conductors": "Copper conductors conforming to UL 83",
                "conduit": "Rigid metal conduit conforming to UL 6",
                "panels": "Dead-front safety switches",
            },
            "part_3_execution": {
                "installation": "Install in accordance with NEC",
                "testing": "Test all circuits and equipment",
                "labeling": "Label all circuits and equipment",
            },
        }

    def _generate_generic_section(
        self, section: str, design_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a generic specification section."""
        return {
            "title": f"SECTION {section}",
            "section_number": section,
            "part_1_general": {
                "summary": f"This section covers requirements for {section}.",
                "references": ["Applicable codes and standards"],
            },
            "part_2_products": {
                "materials": "As specified in design documents",
            },
            "part_3_execution": {
                "installation": "Install in accordance with manufacturer instructions",
                "testing": "Test as required",
            },
        }
