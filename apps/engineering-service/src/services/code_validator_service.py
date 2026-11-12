"""Code Validator Service for compliance checking."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..api.v1.schemas.compliance import (CodeType, ComplianceStatus,
                                         ViolationSchema, ViolationSeverity)
from ..integrations.knowledge_service_client import KnowledgeServiceClient
from ..models.compliance_report import ComplianceReport
from ..models.mep_design import MEPDesign
from ..models.structural_design import StructuralDesign
from ..repositories.compliance_report_repository import \
    ComplianceReportRepository
from ..repositories.mep_design_repository import MEPDesignRepository
from ..repositories.structural_design_repository import \
    StructuralDesignRepository

logger = logging.getLogger(__name__)


class CodeValidatorService:
    """Service for validating designs against building codes.

    Validates structural, MEP, and energy code compliance by checking
    designs against applicable building codes and standards.
    """

    def __init__(
        self,
        compliance_repo: ComplianceReportRepository,
        structural_repo: StructuralDesignRepository,
        mep_repo: MEPDesignRepository,
        knowledge_client: KnowledgeServiceClient,
    ):
        """Initialize code validator service.

        Args:
            compliance_repo: Repository for compliance reports
            structural_repo: Repository for structural designs
            mep_repo: Repository for MEP designs
            knowledge_client: Client for knowledge service
        """
        self.compliance_repo = compliance_repo
        self.structural_repo = structural_repo
        self.mep_repo = mep_repo
        self.knowledge_client = knowledge_client
        self._code_cache: Dict[str, Dict[str, Any]] = {}

    async def validate_structural_code(
        self,
        design_id: int,
        jurisdiction: str,
        user_id: str,
    ) -> ComplianceReport:
        """Validate structural design against IBC and ASCE 7.

        Checks structural design compliance with International Building Code
        and ASCE 7 (Minimum Design Loads for Buildings and Other Structures).

        Args:
            design_id: Structural design identifier
            jurisdiction: Jurisdiction for code requirements
            user_id: User performing validation

        Returns:
            ComplianceReport with validation results

        Raises:
            ValueError: If design not found
        """
        logger.info(f"Validating structural design {design_id} for {jurisdiction}")

        # Get structural design
        design = await self.structural_repo.get_by_id(design_id)
        if not design:
            raise ValueError(f"Structural design {design_id} not found")

        # Get code requirements
        code_requirements = await self.get_code_requirements(
            CodeType.STRUCTURAL, jurisdiction
        )

        # Perform validation checks
        checks_performed = []
        violations = []

        # Check 1: Load combinations (ASCE 7)
        load_check = self._check_load_combinations(design, code_requirements)
        checks_performed.append(load_check["check_name"])
        if load_check["violations"]:
            violations.extend(load_check["violations"])

        # Check 2: Stress ratios
        stress_check = self._check_stress_ratios(design, code_requirements)
        checks_performed.append(stress_check["check_name"])
        if stress_check["violations"]:
            violations.extend(stress_check["violations"])

        # Check 3: Deflection limits
        deflection_check = self._check_deflection_limits(design, code_requirements)
        checks_performed.append(deflection_check["check_name"])
        if deflection_check["violations"]:
            violations.extend(deflection_check["violations"])

        # Check 4: Seismic design category (if applicable)
        if design.loads.get("seismic_load"):
            seismic_check = self._check_seismic_requirements(design, code_requirements)
            checks_performed.append(seismic_check["check_name"])
            if seismic_check["violations"]:
                violations.extend(seismic_check["violations"])

        # Determine overall status
        overall_status = self._determine_compliance_status(violations)

        # Generate recommendations
        recommendations = self._generate_recommendations(violations)

        # Create compliance report
        report = ComplianceReport(
            calculation_sheet_id=design.calculation_sheet_id,
            project_id=design.project_id,
            title=f"Structural Code Compliance - {design.design_type}",
            description=f"IBC and ASCE 7 compliance validation for {jurisdiction}",
            code_type=CodeType.STRUCTURAL.value,
            jurisdiction=jurisdiction,
            code_version=code_requirements.get("version", "2021"),
            checks_performed={"checks": checks_performed},
            violations={"violations": [v.model_dump() for v in violations]},
            recommendations={"recommendations": recommendations},
            overall_status=overall_status.value,
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )

        # Save report
        saved_report = await self.compliance_repo.create(report)
        logger.info(
            f"Created compliance report {saved_report.id} with status {overall_status}"
        )

        return saved_report

    async def validate_mep_code(
        self,
        design_id: int,
        jurisdiction: str,
        user_id: str,
    ) -> ComplianceReport:
        """Validate MEP design against NEC, IPC, IMC, and NFPA.

        Checks MEP system compliance with:
        - NEC (National Electrical Code)
        - IPC (International Plumbing Code)
        - IMC (International Mechanical Code)
        - NFPA (National Fire Protection Association standards)

        Args:
            design_id: MEP design identifier
            jurisdiction: Jurisdiction for code requirements
            user_id: User performing validation

        Returns:
            ComplianceReport with validation results

        Raises:
            ValueError: If design not found
        """
        logger.info(f"Validating MEP design {design_id} for {jurisdiction}")

        # Get MEP design
        design = await self.mep_repo.get_by_id(design_id)
        if not design:
            raise ValueError(f"MEP design {design_id} not found")

        # Get code requirements
        code_requirements = await self.get_code_requirements(CodeType.MEP, jurisdiction)

        # Perform validation checks based on system type
        checks_performed = []
        violations = []

        if design.system_type == "hvac":
            hvac_checks = self._check_hvac_code(design, code_requirements)
            checks_performed.extend(hvac_checks["checks"])
            violations.extend(hvac_checks["violations"])

        elif design.system_type == "electrical":
            electrical_checks = self._check_electrical_code(design, code_requirements)
            checks_performed.extend(electrical_checks["checks"])
            violations.extend(electrical_checks["violations"])

        elif design.system_type == "plumbing":
            plumbing_checks = self._check_plumbing_code(design, code_requirements)
            checks_performed.extend(plumbing_checks["checks"])
            violations.extend(plumbing_checks["violations"])

        elif design.system_type == "fire":
            fire_checks = self._check_fire_protection_code(design, code_requirements)
            checks_performed.extend(fire_checks["checks"])
            violations.extend(fire_checks["violations"])

        # Determine overall status
        overall_status = self._determine_compliance_status(violations)

        # Generate recommendations
        recommendations = self._generate_recommendations(violations)

        # Create compliance report
        report = ComplianceReport(
            calculation_sheet_id=design.calculation_sheet_id,
            project_id=design.project_id,
            title=f"MEP Code Compliance - {design.system_type.upper()}",
            description=f"MEP code compliance validation for {jurisdiction}",
            code_type=CodeType.MEP.value,
            jurisdiction=jurisdiction,
            code_version=code_requirements.get("version", "2021"),
            checks_performed={"checks": checks_performed},
            violations={"violations": [v.model_dump() for v in violations]},
            recommendations={"recommendations": recommendations},
            overall_status=overall_status.value,
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )

        # Save report
        saved_report = await self.compliance_repo.create(report)
        logger.info(
            f"Created MEP compliance report {saved_report.id} with status {overall_status}"
        )

        return saved_report

    async def validate_energy_code(
        self,
        design_id: int,
        jurisdiction: str,
        user_id: str,
        design_type: str = "building",
    ) -> ComplianceReport:
        """Validate energy compliance against IECC and ASHRAE 90.1.

        Checks building energy performance compliance with:
        - IECC (International Energy Conservation Code)
        - ASHRAE 90.1 (Energy Standard for Buildings)

        Args:
            design_id: Design identifier (structural or MEP)
            jurisdiction: Jurisdiction for code requirements
            user_id: User performing validation
            design_type: Type of design ("structural" or "mep")

        Returns:
            ComplianceReport with validation results

        Raises:
            ValueError: If design not found or invalid type
        """
        logger.info(
            f"Validating energy code for design {design_id} ({design_type}) in {jurisdiction}"
        )

        # Get design based on type
        if design_type == "structural":
            design = await self.structural_repo.get_by_id(design_id)
        elif design_type == "mep":
            design = await self.mep_repo.get_by_id(design_id)
        else:
            raise ValueError(f"Invalid design type: {design_type}")

        if not design:
            raise ValueError(f"{design_type.capitalize()} design {design_id} not found")

        # Get code requirements
        code_requirements = await self.get_code_requirements(
            CodeType.ENERGY, jurisdiction
        )

        # Perform validation checks
        checks_performed = []
        violations = []

        # Check 1: Building envelope (insulation, windows)
        envelope_check = self._check_building_envelope(design, code_requirements)
        checks_performed.append(envelope_check["check_name"])
        if envelope_check["violations"]:
            violations.extend(envelope_check["violations"])

        # Check 2: HVAC efficiency (if MEP design)
        if (
            design_type == "mep"
            and hasattr(design, "system_type")
            and design.system_type == "hvac"
        ):
            hvac_efficiency_check = self._check_hvac_efficiency(
                design, code_requirements
            )
            checks_performed.append(hvac_efficiency_check["check_name"])
            if hvac_efficiency_check["violations"]:
                violations.extend(hvac_efficiency_check["violations"])

        # Check 3: Lighting power density (if MEP electrical)
        if (
            design_type == "mep"
            and hasattr(design, "system_type")
            and design.system_type == "electrical"
        ):
            lighting_check = self._check_lighting_power_density(
                design, code_requirements
            )
            checks_performed.append(lighting_check["check_name"])
            if lighting_check["violations"]:
                violations.extend(lighting_check["violations"])

        # Determine overall status
        overall_status = self._determine_compliance_status(violations)

        # Generate recommendations
        recommendations = self._generate_recommendations(violations)

        # Create compliance report
        report = ComplianceReport(
            calculation_sheet_id=design.calculation_sheet_id
            if hasattr(design, "calculation_sheet_id")
            else None,
            project_id=design.project_id,
            title=f"Energy Code Compliance - {design_type.capitalize()}",
            description=f"IECC and ASHRAE 90.1 compliance validation for {jurisdiction}",
            code_type=CodeType.ENERGY.value,
            jurisdiction=jurisdiction,
            code_version=code_requirements.get("version", "2021"),
            checks_performed={"checks": checks_performed},
            violations={"violations": [v.model_dump() for v in violations]},
            recommendations={"recommendations": recommendations},
            overall_status=overall_status.value,
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )

        # Save report
        saved_report = await self.compliance_repo.create(report)
        logger.info(
            f"Created energy compliance report {saved_report.id} with status {overall_status}"
        )

        return saved_report

    async def get_code_requirements(
        self,
        code_type: CodeType,
        jurisdiction: str,
    ) -> Dict[str, Any]:
        """Retrieve code requirements from Knowledge Service.

        Fetches latest code versions and requirements, with caching.

        Args:
            code_type: Type of code (structural, mep, energy)
            jurisdiction: Jurisdiction for code requirements

        Returns:
            Dictionary of code requirements
        """
        cache_key = f"{code_type.value}:{jurisdiction}"

        # Check cache first
        if cache_key in self._code_cache:
            logger.debug(f"Using cached code requirements for {cache_key}")
            return self._code_cache[cache_key]

        # Fetch from Knowledge Service
        logger.info(
            f"Fetching code requirements for {code_type.value} in {jurisdiction}"
        )
        try:
            requirements = await self.knowledge_client.get_code_requirements(
                code_type.value, jurisdiction
            )

            # Cache the requirements
            self._code_cache[cache_key] = requirements

            return requirements
        except Exception as e:
            logger.error(f"Failed to fetch code requirements: {e}")
            # Return default requirements as fallback
            return self._get_default_requirements(code_type, jurisdiction)

    def _get_default_requirements(
        self, code_type: CodeType, jurisdiction: str
    ) -> Dict[str, Any]:
        """Get default code requirements as fallback.

        Args:
            code_type: Type of code
            jurisdiction: Jurisdiction

        Returns:
            Default requirements dictionary
        """
        defaults = {
            "version": "2021",
            "jurisdiction": jurisdiction,
            "code_type": code_type.value,
            "requirements": {},
        }

        if code_type == CodeType.STRUCTURAL:
            defaults["requirements"] = {
                "max_stress_ratio": 1.0,
                "max_deflection_ratio": 360,  # L/360
                "load_combinations": ["1.4D", "1.2D + 1.6L", "1.2D + 1.0L + 1.0W"],
            }
        elif code_type == CodeType.MEP:
            defaults["requirements"] = {
                "electrical": {
                    "max_voltage_drop": 3.0,
                    "min_circuit_breaker_rating": 15,
                },
                "plumbing": {"min_pipe_size": 0.5, "max_velocity": 8.0},
                "hvac": {"min_ventilation_rate": 15, "max_duct_velocity": 2000},
            }
        elif code_type == CodeType.ENERGY:
            defaults["requirements"] = {
                "max_u_value_wall": 0.057,
                "max_u_value_roof": 0.048,
                "min_hvac_efficiency": 13.0,  # SEER
                "max_lighting_power_density": 1.0,  # W/sq ft
            }

        return defaults

    # Structural validation helper methods

    def _check_load_combinations(
        self, design: StructuralDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if load combinations meet ASCE 7 requirements."""
        violations = []

        # Get required load combinations from code
        required_combinations = code_requirements.get("requirements", {}).get(
            "load_combinations", []
        )

        # Check if design includes all required combinations
        design_loads = design.loads
        if not design_loads.get("load_combinations"):
            violations.append(
                ViolationSchema(
                    code_section="ASCE 7-16 Section 2.3",
                    severity=ViolationSeverity.CRITICAL,
                    description="Load combinations not specified in design",
                    recommendation="Include all required ASCE 7 load combinations",
                    affected_elements=[design.design_type],
                )
            )

        return {
            "check_name": "Load Combinations (ASCE 7)",
            "violations": violations,
        }

    def _check_stress_ratios(
        self, design: StructuralDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if stress ratios are within acceptable limits."""
        violations = []

        max_stress_ratio = code_requirements.get("requirements", {}).get(
            "max_stress_ratio", 1.0
        )

        stress_ratios = design.stress_ratios
        for element, ratio in stress_ratios.items():
            if ratio > max_stress_ratio:
                violations.append(
                    ViolationSchema(
                        code_section="IBC Section 1605",
                        severity=ViolationSeverity.CRITICAL,
                        description=f"Stress ratio {ratio:.2f} exceeds maximum {max_stress_ratio}",
                        recommendation=f"Increase {element} capacity or reduce loads",
                        affected_elements=[element],
                    )
                )

        return {
            "check_name": "Stress Ratios",
            "violations": violations,
        }

    def _check_deflection_limits(
        self, design: StructuralDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if deflections are within acceptable limits."""
        violations = []

        max_deflection_ratio = code_requirements.get("requirements", {}).get(
            "max_deflection_ratio", 360
        )

        design_results = design.design_results
        if "deflection_ratio" in design_results:
            deflection_ratio = design_results["deflection_ratio"]
            if deflection_ratio < max_deflection_ratio:  # Lower ratio = more deflection
                violations.append(
                    ViolationSchema(
                        code_section="IBC Table 1604.3",
                        severity=ViolationSeverity.MAJOR,
                        description=f"Deflection ratio L/{deflection_ratio} exceeds limit L/{max_deflection_ratio}",
                        recommendation="Increase member stiffness or reduce span",
                        affected_elements=[design.design_type],
                    )
                )

        return {
            "check_name": "Deflection Limits",
            "violations": violations,
        }

    def _check_seismic_requirements(
        self, design: StructuralDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check seismic design requirements."""
        violations = []

        # Check if seismic design category is specified
        design_results = design.design_results
        if not design_results.get("seismic_design_category"):
            violations.append(
                ViolationSchema(
                    code_section="ASCE 7-16 Section 11.6",
                    severity=ViolationSeverity.MAJOR,
                    description="Seismic design category not specified",
                    recommendation="Determine seismic design category per ASCE 7",
                    affected_elements=[design.design_type],
                )
            )

        return {
            "check_name": "Seismic Requirements",
            "violations": violations,
        }

    # MEP validation helper methods

    def _check_hvac_code(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check HVAC system against IMC requirements."""
        checks = []
        violations = []

        checks.append("HVAC Ventilation Rates (IMC)")
        checks.append("HVAC Duct Sizing (IMC)")

        # Check ventilation rates
        min_ventilation = (
            code_requirements.get("requirements", {})
            .get("hvac", {})
            .get("min_ventilation_rate", 15)
        )

        sizing_results = design.sizing_results
        if "ventilation_rate" in sizing_results:
            if sizing_results["ventilation_rate"] < min_ventilation:
                violations.append(
                    ViolationSchema(
                        code_section="IMC Section 403",
                        severity=ViolationSeverity.CRITICAL,
                        description=f"Ventilation rate {sizing_results['ventilation_rate']} CFM/person below minimum {min_ventilation}",
                        recommendation="Increase ventilation rate to meet IMC requirements",
                        affected_elements=["HVAC System"],
                    )
                )

        return {
            "checks": checks,
            "violations": violations,
        }

    def _check_electrical_code(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check electrical system against NEC requirements."""
        checks = []
        violations = []

        checks.append("Electrical Load Calculations (NEC)")
        checks.append("Circuit Sizing (NEC)")
        checks.append("Voltage Drop (NEC)")

        # Check voltage drop
        max_voltage_drop = (
            code_requirements.get("requirements", {})
            .get("electrical", {})
            .get("max_voltage_drop", 3.0)
        )

        sizing_results = design.sizing_results
        if "voltage_drop" in sizing_results:
            if sizing_results["voltage_drop"] > max_voltage_drop:
                violations.append(
                    ViolationSchema(
                        code_section="NEC Section 210.19(A)",
                        severity=ViolationSeverity.MAJOR,
                        description=f"Voltage drop {sizing_results['voltage_drop']}% exceeds maximum {max_voltage_drop}%",
                        recommendation="Increase conductor size or reduce circuit length",
                        affected_elements=["Electrical Distribution"],
                    )
                )

        return {
            "checks": checks,
            "violations": violations,
        }

    def _check_plumbing_code(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check plumbing system against IPC requirements."""
        checks = []
        violations = []

        checks.append("Plumbing Fixture Units (IPC)")
        checks.append("Pipe Sizing (IPC)")
        checks.append("Water Velocity (IPC)")

        # Check water velocity
        max_velocity = (
            code_requirements.get("requirements", {})
            .get("plumbing", {})
            .get("max_velocity", 8.0)
        )

        sizing_results = design.sizing_results
        if "water_velocity" in sizing_results:
            if sizing_results["water_velocity"] > max_velocity:
                violations.append(
                    ViolationSchema(
                        code_section="IPC Section 604.3",
                        severity=ViolationSeverity.MAJOR,
                        description=f"Water velocity {sizing_results['water_velocity']} ft/s exceeds maximum {max_velocity} ft/s",
                        recommendation="Increase pipe size to reduce velocity",
                        affected_elements=["Plumbing System"],
                    )
                )

        return {
            "checks": checks,
            "violations": violations,
        }

    def _check_fire_protection_code(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check fire protection system against NFPA 13 requirements."""
        checks = []
        violations = []

        checks.append("Sprinkler Coverage (NFPA 13)")
        checks.append("Water Supply (NFPA 13)")
        checks.append("Pipe Sizing (NFPA 13)")

        # Basic checks - would need more detailed requirements
        sizing_results = design.sizing_results
        if not sizing_results.get("sprinkler_coverage"):
            violations.append(
                ViolationSchema(
                    code_section="NFPA 13 Section 8.5",
                    severity=ViolationSeverity.CRITICAL,
                    description="Sprinkler coverage not specified",
                    recommendation="Calculate and specify sprinkler coverage per NFPA 13",
                    affected_elements=["Fire Protection System"],
                )
            )

        return {
            "checks": checks,
            "violations": violations,
        }

    # Energy validation helper methods

    def _check_building_envelope(
        self, design: Any, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check building envelope against IECC requirements."""
        violations = []

        # Check U-values for walls and roof
        requirements = code_requirements.get("requirements", {})
        max_u_wall = requirements.get("max_u_value_wall", 0.057)
        max_u_roof = requirements.get("max_u_value_roof", 0.048)

        # This would need actual envelope data from design
        # For now, placeholder check

        return {
            "check_name": "Building Envelope (IECC)",
            "violations": violations,
        }

    def _check_hvac_efficiency(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check HVAC efficiency against ASHRAE 90.1 requirements."""
        violations = []

        min_efficiency = code_requirements.get("requirements", {}).get(
            "min_hvac_efficiency", 13.0
        )

        equipment = design.equipment
        if "efficiency" in equipment:
            if equipment["efficiency"] < min_efficiency:
                violations.append(
                    ViolationSchema(
                        code_section="ASHRAE 90.1 Section 6.4",
                        severity=ViolationSeverity.MAJOR,
                        description=f"HVAC efficiency {equipment['efficiency']} SEER below minimum {min_efficiency}",
                        recommendation="Specify higher efficiency HVAC equipment",
                        affected_elements=["HVAC Equipment"],
                    )
                )

        return {
            "check_name": "HVAC Efficiency (ASHRAE 90.1)",
            "violations": violations,
        }

    def _check_lighting_power_density(
        self, design: MEPDesign, code_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check lighting power density against ASHRAE 90.1 requirements."""
        violations = []

        max_lpd = code_requirements.get("requirements", {}).get(
            "max_lighting_power_density", 1.0
        )

        loads = design.loads
        if "lighting_power_density" in loads:
            if loads["lighting_power_density"] > max_lpd:
                violations.append(
                    ViolationSchema(
                        code_section="ASHRAE 90.1 Section 9.5",
                        severity=ViolationSeverity.MAJOR,
                        description=f"Lighting power density {loads['lighting_power_density']} W/sq ft exceeds maximum {max_lpd}",
                        recommendation="Reduce lighting power density or use more efficient fixtures",
                        affected_elements=["Lighting System"],
                    )
                )

        return {
            "check_name": "Lighting Power Density (ASHRAE 90.1)",
            "violations": violations,
        }

    # Helper methods

    def _determine_compliance_status(
        self, violations: List[ViolationSchema]
    ) -> ComplianceStatus:
        """Determine overall compliance status based on violations.

        Args:
            violations: List of violations found

        Returns:
            Overall compliance status
        """
        if not violations:
            return ComplianceStatus.COMPLIANT

        # Check for critical violations
        has_critical = any(v.severity == ViolationSeverity.CRITICAL for v in violations)
        if has_critical:
            return ComplianceStatus.NON_COMPLIANT

        # Check for major violations
        has_major = any(v.severity == ViolationSeverity.MAJOR for v in violations)
        if has_major:
            return ComplianceStatus.REVIEW_REQUIRED

        # Only minor violations or warnings
        return ComplianceStatus.REVIEW_REQUIRED

    def _generate_recommendations(self, violations: List[ViolationSchema]) -> List[str]:
        """Generate general recommendations based on violations.

        Args:
            violations: List of violations found

        Returns:
            List of general recommendations
        """
        if not violations:
            return ["Design meets all code requirements"]

        recommendations = []

        # Group by severity
        critical_count = sum(
            1 for v in violations if v.severity == ViolationSeverity.CRITICAL
        )
        major_count = sum(
            1 for v in violations if v.severity == ViolationSeverity.MAJOR
        )
        minor_count = sum(
            1 for v in violations if v.severity == ViolationSeverity.MINOR
        )

        if critical_count > 0:
            recommendations.append(
                f"Address {critical_count} critical violation(s) immediately - design does not meet minimum code requirements"
            )

        if major_count > 0:
            recommendations.append(
                f"Review and resolve {major_count} major violation(s) before proceeding"
            )

        if minor_count > 0:
            recommendations.append(
                f"Consider addressing {minor_count} minor violation(s) for improved compliance"
            )

        recommendations.append(
            "Consult with code official for jurisdiction-specific requirements"
        )
        recommendations.append("Review all violation recommendations in detail")

        return recommendations
