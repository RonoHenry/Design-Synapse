"""Compliance checking service for building code validation."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import ViolationDetail, WarningDetail
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.knowledge_service_client import KnowledgeServiceClient
from src.models.compliance_check import ComplianceCheck
from src.models.design import Design
from src.repositories.compliance_check_repository import \
    ComplianceCheckRepository
from src.repositories.design_repository import DesignRepository

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service for building code compliance checking.

    Handles compliance check initiation, code validation logic,
    result retrieval, and compliance report generation.
    """

    def __init__(
        self,
        compliance_repository: ComplianceCheckRepository,
        design_repository: DesignRepository,
        knowledge_client: KnowledgeServiceClient,
    ):
        """
        Initialize ComplianceService.

        Args:
            compliance_repository: Repository for compliance check data
            design_repository: Repository for design data
            knowledge_client: Client for knowledge service integration
        """
        self.compliance_repository = compliance_repository
        self.design_repository = design_repository
        self.knowledge_client = knowledge_client

    async def check_compliance(
        self,
        design_id: UUID,
        standards: List[str],
        jurisdiction: Optional[str] = None,
    ) -> ComplianceCheck:
        """
        Initiate compliance check for a design.

        Validates design exists, creates compliance check record,
        and starts asynchronous compliance validation process.

        Args:
            design_id: Design ID to check compliance for
            standards: List of code standards to check against
            jurisdiction: Optional jurisdiction for local requirements

        Returns:
            ComplianceCheck model instance

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If design is not in valid state for checking
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot check compliance for deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Create compliance check record
        compliance_check = ComplianceCheck(
            id=str(uuid4()),
            design_id=str(design_id),
            design_version=design.current_version,
            code_standards=standards,
            jurisdiction=jurisdiction,
            status="pending",
            violations=[],
            warnings=[],
            recommendations=[],
            started_at=datetime.utcnow(),
        )

        # Save compliance check
        compliance_check = await self.compliance_repository.create(compliance_check)

        logger.info(
            f"Created compliance check {compliance_check.id} for design {design_id}"
        )

        # Start asynchronous compliance validation
        # In a real implementation, this would be queued as a background task
        try:
            await self._perform_compliance_validation(compliance_check, design)
        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            # Update status to failed
            compliance_check.status = "failed"
            compliance_check.completed_at = datetime.utcnow()
            await self.compliance_repository.update(
                compliance_check.id, status="failed", completed_at=datetime.utcnow()
            )

        # Return the model instance
        return compliance_check

    async def validate_against_code(
        self,
        design: Design,
        code_standard: str,
        jurisdiction: Optional[str] = None,
    ) -> tuple[List[ViolationDetail], List[WarningDetail]]:
        """
        Validate design against specific building code standard.

        Retrieves applicable code sections and validates design elements
        against code requirements.

        Args:
            design: Design to validate
            code_standard: Code standard to validate against
            jurisdiction: Optional jurisdiction for local requirements

        Returns:
            Tuple of (violations, warnings) found during validation

        Raises:
            ValidationError: If code validation fails
        """
        violations = []
        warnings = []

        try:
            # Get applicable codes for the design
            location = self._extract_location_string(design)
            applicable_codes = await self.knowledge_client.get_applicable_codes(
                location=location or jurisdiction or "General",
                building_type=design.building_type,
            )

            # Filter for the specific code standard
            target_code = None
            for code in applicable_codes:
                if code_standard in code.name or code_standard in code.code_id:
                    target_code = code
                    break

            if target_code is None:
                logger.warning(
                    f"Code standard {code_standard} not found for "
                    f"location {location}, building type {design.building_type}"
                )
                return violations, warnings

            # Perform specific code validations based on building type and design data
            violations.extend(
                await self._validate_building_code_requirements(
                    design, target_code, jurisdiction
                )
            )

            # Check for accessibility requirements if ADA is in code standards
            if "ADA" in code_standard or "accessibility" in code_standard.lower():
                accessibility_violations = (
                    await self._validate_accessibility_requirements(design, target_code)
                )
                violations.extend(accessibility_violations)

            # Generate warnings for potential issues
            warnings.extend(await self._generate_code_warnings(design, target_code))

        except Exception as e:
            logger.error(f"Code validation failed for {code_standard}: {e}")
            raise ValidationError(
                f"Failed to validate against code {code_standard}: {str(e)}",
                details={"code_standard": code_standard, "error": str(e)},
            )

        return violations, warnings

    async def get_check_results(self, check_id: UUID) -> ComplianceCheck:
        """
        Retrieve compliance check results.

        Args:
            check_id: Compliance check ID

        Returns:
            ComplianceCheck model instance

        Raises:
            NotFoundError: If compliance check doesn't exist
        """
        compliance_check = await self.compliance_repository.get(str(check_id))
        if compliance_check is None:
            raise NotFoundError(
                f"Compliance check {check_id} not found",
                details={"check_id": str(check_id)},
            )

        return compliance_check

    async def list_checks_for_design(self, design_id: UUID) -> List[ComplianceCheck]:
        """
        List all compliance checks for a design.

        Args:
            design_id: Design ID to list checks for

        Returns:
            List of compliance checks for the design

        Raises:
            NotFoundError: If design doesn't exist
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Get all compliance checks for the design
        compliance_checks = await self.compliance_repository.list_by_design(
            str(design_id)
        )

        return compliance_checks

    async def generate_compliance_report(self, check_id: UUID) -> str:
        """
        Generate detailed compliance report.

        Creates comprehensive compliance report with violations,
        recommendations, and remediation guidance.

        Args:
            check_id: Compliance check ID

        Returns:
            URL to generated compliance report

        Raises:
            NotFoundError: If compliance check doesn't exist
            ValidationError: If check is not completed
        """
        compliance_check = await self.compliance_repository.get(str(check_id))
        if compliance_check is None:
            raise NotFoundError(
                f"Compliance check {check_id} not found",
                details={"check_id": str(check_id)},
            )

        if compliance_check.status != "completed":
            raise ValidationError(
                f"Cannot generate report for incomplete check {check_id}",
                details={"check_id": str(check_id), "status": compliance_check.status},
            )

        # In a real implementation, this would generate a PDF report
        # and upload it to a storage service
        report_url = f"/api/v1/compliance-checks/{check_id}/report.pdf"

        # Update compliance check with report URL
        compliance_check.report_url = report_url
        await self.compliance_repository.update(
            compliance_check.id, report_url=report_url
        )

        logger.info(f"Generated compliance report for check {check_id}")

        return report_url

    async def _perform_compliance_validation(
        self, compliance_check: ComplianceCheck, design: Design
    ) -> None:
        """
        Perform the actual compliance validation.

        This is the core validation logic that checks the design
        against all specified code standards.

        Args:
            compliance_check: Compliance check record to update
            design: Design to validate
        """
        try:
            # Update status to in_progress
            compliance_check.status = "in_progress"
            await self.compliance_repository.update(
                compliance_check.id, status="in_progress"
            )

            all_violations = []
            all_warnings = []

            # Validate against each code standard
            for code_standard in compliance_check.code_standards:
                violations, warnings = await self.validate_against_code(
                    design, code_standard, compliance_check.jurisdiction
                )
                all_violations.extend(violations)
                all_warnings.extend(warnings)

            # Convert to JSON-serializable format
            violations_data = [v.model_dump() for v in all_violations]
            warnings_data = [w.model_dump() for w in all_warnings]

            # Generate recommendations based on violations
            recommendations = self._generate_recommendations(all_violations)

            # Determine overall pass/fail status
            passed = len(all_violations) == 0

            # Update compliance check with results
            compliance_check.status = "completed"
            compliance_check.passed = passed
            compliance_check.violations = violations_data
            compliance_check.warnings = warnings_data
            compliance_check.recommendations = recommendations
            compliance_check.completed_at = datetime.utcnow()

            await self.compliance_repository.update(
                compliance_check.id,
                status="completed",
                passed=passed,
                violations=violations_data,
                warnings=warnings_data,
                recommendations=recommendations,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Completed compliance check {compliance_check.id}: "
                f"passed={passed}, violations={len(all_violations)}, "
                f"warnings={len(all_warnings)}"
            )

        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            # Update status to failed
            await self.compliance_repository.update(
                compliance_check.id,
                status="failed",
                completed_at=datetime.utcnow(),
            )
            raise

    async def _validate_building_code_requirements(
        self, design: Design, code: any, jurisdiction: Optional[str]
    ) -> List[ViolationDetail]:
        """
        Validate design against building code requirements.

        Args:
            design: Design to validate
            code: Code standard to validate against
            jurisdiction: Optional jurisdiction

        Returns:
            List of violations found
        """
        violations = []

        # Example validation logic - in a real implementation,
        # this would be much more comprehensive

        # Check occupancy limits based on building type
        if design.building_type == "commercial":
            # Example: Check for egress width requirements
            violations.append(
                ViolationDetail(
                    code_section="IBC 1005.1",
                    description="Egress width calculation required",
                    severity="major",
                    location="Main entrance",
                    remediation="Provide egress width calculation based on occupant load",
                )
            )

        # Check for fire separation requirements
        if design.building_type in ["residential", "mixed_use"]:
            violations.append(
                ViolationDetail(
                    code_section="IBC 706.3",
                    description="Fire separation between occupancies required",
                    severity="critical",
                    location="Between residential and commercial areas",
                    remediation="Provide 2-hour fire-rated separation",
                )
            )

        return violations

    async def _validate_accessibility_requirements(
        self, design: Design, code: any
    ) -> List[ViolationDetail]:
        """
        Validate design against accessibility requirements.

        Args:
            design: Design to validate
            code: Code standard

        Returns:
            List of accessibility violations
        """
        violations = []

        # Example accessibility validations
        violations.append(
            ViolationDetail(
                code_section="ADA 404.2.3",
                description="Door opening force exceeds maximum",
                severity="major",
                location="Main entrance door",
                remediation="Reduce door opening force to 5 lbf maximum",
            )
        )

        return violations

    async def _generate_code_warnings(
        self, design: Design, code: any
    ) -> List[WarningDetail]:
        """
        Generate warnings for potential code issues.

        Args:
            design: Design to check
            code: Code standard

        Returns:
            List of warnings
        """
        warnings = []

        # Example warning generation
        warnings.append(
            WarningDetail(
                code_section="IBC 1208.3",
                description="Natural ventilation may not meet requirements",
                recommendation="Consider mechanical ventilation system",
            )
        )

        return warnings

    def _generate_recommendations(self, violations: List[ViolationDetail]) -> List[str]:
        """
        Generate general recommendations based on violations.

        Args:
            violations: List of violations found

        Returns:
            List of general recommendations
        """
        recommendations = []

        if violations:
            recommendations.append(
                "Review design with licensed architect for code compliance"
            )
            recommendations.append(
                "Consult with local building department for jurisdiction-specific requirements"
            )

        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            recommendations.append(
                "Address critical violations before proceeding with construction documents"
            )

        return recommendations

    def _extract_location_string(self, design: Design) -> Optional[str]:
        """
        Extract location string from design for code lookup.

        Args:
            design: Design with location data

        Returns:
            Location string or None
        """
        if not design.location_data:
            return None

        location_parts = []
        if design.location_data.get("city"):
            location_parts.append(design.location_data["city"])
        if design.location_data.get("state"):
            location_parts.append(design.location_data["state"])
        if design.location_data.get("country"):
            location_parts.append(design.location_data["country"])

        return ", ".join(location_parts) if location_parts else None
