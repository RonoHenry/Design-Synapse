"""Energy efficiency analysis service for building energy performance evaluation."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import (BuildingParameters,
                                         EfficiencyRecommendation,
                                         EnergyAnalysisRequest,
                                         EnergyAnalysisResponse,
                                         EnergyEstimate, EnvelopeMetrics)
from src.api.v1.schemas.enums import CheckStatus
from src.core.exceptions import NotFoundError, ValidationError
from src.models.design import Design
from src.models.energy_analysis import EnergyAnalysis
from src.repositories.design_repository import DesignRepository
from src.repositories.energy_analysis_repository import \
    EnergyAnalysisRepository

logger = logging.getLogger(__name__)


class EnergyAnalysisService:
    """
    Service for energy efficiency analysis.

    Handles energy analysis initiation, envelope performance calculation,
    energy consumption estimation, and efficiency recommendations.
    """

    def __init__(
        self,
        energy_repository: EnergyAnalysisRepository,
        design_repository: DesignRepository,
    ):
        """
        Initialize EnergyAnalysisService.

        Args:
            energy_repository: Repository for energy analysis data
            design_repository: Repository for design data
        """
        self.energy_repository = energy_repository
        self.design_repository = design_repository

    async def analyze_energy(
        self,
        design_id: UUID,
        request: EnergyAnalysisRequest,
    ) -> EnergyAnalysisResponse:
        """
        Initiate energy efficiency analysis for a design.

        Validates design exists, creates energy analysis record,
        and starts asynchronous energy analysis process.

        Args:
            design_id: Design ID to analyze energy for
            request: Energy analysis request parameters

        Returns:
            EnergyAnalysisResponse with analysis details

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If design is not in valid state for analysis
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
                f"Cannot analyze energy for deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Create energy analysis record
        energy_analysis = EnergyAnalysis(
            id=str(uuid4()),
            design_id=str(design_id),
            design_version=design.current_version,
            standards=request.standards,
            climate_zone=request.climate_zone,
            status="pending",
            envelope_performance={},
            energy_consumption={},
            recommendations=[],
            certificate_url=None,
            started_at=datetime.utcnow(),
        )

        # Save energy analysis
        energy_analysis = await self.energy_repository.create(energy_analysis)

        logger.info(
            f"Created energy analysis {energy_analysis.id} for design {design_id}"
        )

        # Start asynchronous energy analysis
        # In a real implementation, this would be queued as a background task
        try:
            await self._perform_energy_analysis(
                energy_analysis, design, request.building_parameters
            )
        except Exception as e:
            logger.error(f"Energy analysis failed: {e}")
            # Update status to failed
            energy_analysis.status = "failed"
            energy_analysis.completed_at = datetime.utcnow()
            await self.energy_repository.update(
                energy_analysis.id, status="failed", completed_at=datetime.utcnow()
            )

        # Return response
        return self._build_energy_response(energy_analysis)

    async def calculate_envelope_performance(
        self,
        design: Design,
        building_parameters: BuildingParameters,
        climate_zone: str,
    ) -> EnvelopeMetrics:
        """
        Calculate building envelope performance including R-values and U-factors.

        Analyzes wall assemblies, roof assemblies, windows, and doors
        to determine thermal performance characteristics.

        Args:
            design: Design to calculate envelope performance for
            building_parameters: Building parameters for analysis
            climate_zone: Climate zone for analysis

        Returns:
            EnvelopeMetrics with calculated performance values

        Raises:
            ValidationError: If envelope calculation fails
        """
        try:
            # Extract envelope data from design
            envelope_data = self._extract_envelope_data_from_design(design)

            # Calculate wall R-value
            wall_r_value = await self._calculate_wall_r_value(
                envelope_data.get("walls", {}), climate_zone
            )

            # Calculate roof R-value
            roof_r_value = await self._calculate_roof_r_value(
                envelope_data.get("roof", {}), climate_zone
            )

            # Calculate window U-factor
            window_u_factor = await self._calculate_window_u_factor(
                envelope_data.get("windows", {}), climate_zone
            )

            # Calculate infiltration rate
            infiltration_rate = await self._calculate_infiltration_rate(
                envelope_data, building_parameters
            )

            return EnvelopeMetrics(
                wall_r_value=wall_r_value,
                roof_r_value=roof_r_value,
                window_u_factor=window_u_factor,
                infiltration_rate=infiltration_rate,
            )

        except Exception as e:
            logger.error(f"Envelope performance calculation failed: {e}")
            raise ValidationError(
                f"Failed to calculate envelope performance: {str(e)}",
                details={"error": str(e)},
            )

    async def estimate_consumption(
        self,
        design: Design,
        building_parameters: BuildingParameters,
        envelope_metrics: EnvelopeMetrics,
        climate_zone: str,
    ) -> EnergyEstimate:
        """
        Estimate annual energy consumption based on building characteristics.

        Calculates heating, cooling, lighting, and equipment energy use
        based on building type, envelope performance, and climate zone.

        Args:
            design: Design to estimate consumption for
            building_parameters: Building parameters for analysis
            envelope_metrics: Calculated envelope performance
            climate_zone: Climate zone for analysis

        Returns:
            EnergyEstimate with consumption breakdown and costs

        Raises:
            ValidationError: If consumption estimation fails
        """
        try:
            # Get climate data for zone
            climate_data = self._get_climate_data(climate_zone)

            # Calculate heating energy
            heating_kwh = await self._calculate_heating_energy(
                building_parameters, envelope_metrics, climate_data
            )

            # Calculate cooling energy
            cooling_kwh = await self._calculate_cooling_energy(
                building_parameters, envelope_metrics, climate_data
            )

            # Calculate lighting energy
            lighting_kwh = await self._calculate_lighting_energy(
                building_parameters, design.building_type
            )

            # Calculate equipment energy
            equipment_kwh = await self._calculate_equipment_energy(
                building_parameters, design.building_type
            )

            # Calculate total consumption
            annual_consumption_kwh = (
                heating_kwh + cooling_kwh + lighting_kwh + equipment_kwh
            )

            # Estimate cost (using average rate of $0.12/kWh)
            energy_rate = Decimal("0.12")
            estimated_cost = Decimal(str(annual_consumption_kwh)) * energy_rate

            return EnergyEstimate(
                annual_consumption_kwh=annual_consumption_kwh,
                heating_kwh=heating_kwh,
                cooling_kwh=cooling_kwh,
                lighting_kwh=lighting_kwh,
                equipment_kwh=equipment_kwh,
                estimated_cost=estimated_cost,
            )

        except Exception as e:
            logger.error(f"Energy consumption estimation failed: {e}")
            raise ValidationError(
                f"Failed to estimate energy consumption: {str(e)}",
                details={"error": str(e)},
            )

    async def generate_certificate(
        self,
        analysis_id: UUID,
        envelope_metrics: EnvelopeMetrics,
        energy_estimate: EnergyEstimate,
        standards: List[str],
    ) -> str:
        """
        Generate energy performance certificate.

        Creates a PDF certificate documenting the building's energy
        performance and compliance with energy standards.

        Args:
            analysis_id: Energy analysis ID
            envelope_metrics: Calculated envelope performance
            energy_estimate: Energy consumption estimate
            standards: Energy standards used

        Returns:
            URL to generated certificate

        Raises:
            ValidationError: If certificate generation fails
        """
        try:
            # In a real implementation, this would generate a PDF certificate
            # For now, we'll return a placeholder URL
            certificate_url = (
                f"https://certificates.example.com/energy/{analysis_id}.pdf"
            )

            logger.info(f"Generated energy certificate for analysis {analysis_id}")

            return certificate_url

        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            raise ValidationError(
                f"Failed to generate energy certificate: {str(e)}",
                details={"error": str(e)},
            )

    async def get_analysis_results(self, analysis_id: UUID) -> EnergyAnalysisResponse:
        """
        Retrieve energy analysis results.

        Args:
            analysis_id: Energy analysis ID

        Returns:
            EnergyAnalysisResponse with current analysis status and results

        Raises:
            NotFoundError: If energy analysis doesn't exist
        """
        energy_analysis = await self.energy_repository.get(str(analysis_id))
        if energy_analysis is None:
            raise NotFoundError(
                f"Energy analysis {analysis_id} not found",
                details={"analysis_id": str(analysis_id)},
            )

        return self._build_energy_response(energy_analysis)

    async def _perform_energy_analysis(
        self,
        energy_analysis: EnergyAnalysis,
        design: Design,
        building_parameters: BuildingParameters,
    ) -> None:
        """
        Perform the actual energy analysis.

        This is the core analysis logic that calculates envelope performance,
        estimates energy consumption, and generates recommendations.

        Args:
            energy_analysis: Energy analysis record to update
            design: Design to analyze
            building_parameters: Building parameters for analysis
        """
        try:
            # Update status to in_progress
            energy_analysis.status = "in_progress"
            await self.energy_repository.update(
                energy_analysis.id, status="in_progress"
            )

            # Calculate envelope performance
            envelope_metrics = await self.calculate_envelope_performance(
                design, building_parameters, energy_analysis.climate_zone
            )

            # Estimate energy consumption
            energy_estimate = await self.estimate_consumption(
                design,
                building_parameters,
                envelope_metrics,
                energy_analysis.climate_zone,
            )

            # Generate efficiency recommendations
            recommendations = await self._generate_efficiency_recommendations(
                envelope_metrics, energy_estimate, energy_analysis.standards
            )

            # Generate certificate
            certificate_url = await self.generate_certificate(
                UUID(energy_analysis.id),
                envelope_metrics,
                energy_estimate,
                energy_analysis.standards,
            )

            # Convert to JSON-serializable format
            envelope_data = envelope_metrics.model_dump()
            consumption_data = energy_estimate.model_dump()
            recommendations_data = [r.model_dump() for r in recommendations]

            # Update energy analysis with results
            energy_analysis.status = "completed"
            energy_analysis.envelope_performance = envelope_data
            energy_analysis.energy_consumption = consumption_data
            energy_analysis.recommendations = recommendations_data
            energy_analysis.certificate_url = certificate_url
            energy_analysis.completed_at = datetime.utcnow()

            await self.energy_repository.update(
                energy_analysis.id,
                status="completed",
                envelope_performance=envelope_data,
                energy_consumption=consumption_data,
                recommendations=recommendations_data,
                certificate_url=certificate_url,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Completed energy analysis {energy_analysis.id}: "
                f"consumption={energy_estimate.annual_consumption_kwh:.0f} kWh/year, "
                f"cost=${energy_estimate.estimated_cost:.2f}/year"
            )

        except Exception as e:
            logger.error(f"Energy analysis failed: {e}")
            # Update status to failed
            await self.energy_repository.update(
                energy_analysis.id,
                status="failed",
                completed_at=datetime.utcnow(),
            )
            raise

    def _extract_envelope_data_from_design(self, design: Design) -> Dict:
        """
        Extract envelope data from design metadata.

        Args:
            design: Design to extract envelope data from

        Returns:
            Dictionary with envelope component data
        """
        # In a real implementation, this would parse actual design data
        # For now, we'll use example data based on building type
        envelope_data = {
            "walls": {
                "construction_type": "wood_frame",
                "insulation_r_value": 13.0,  # R-13 batt insulation
                "sheathing_r_value": 0.6,  # OSB sheathing
                "siding_r_value": 0.8,  # Vinyl siding
                "interior_finish_r_value": 0.9,  # Drywall
                "air_film_r_values": 1.0,  # Interior and exterior air films
            },
            "roof": {
                "construction_type": "pitched_roof",
                "insulation_r_value": 30.0,  # R-30 blown insulation
                "sheathing_r_value": 0.6,  # Plywood sheathing
                "roofing_r_value": 0.4,  # Asphalt shingles
                "air_film_r_values": 1.2,  # Air films
            },
            "windows": {
                "glazing_type": "double_pane",
                "frame_type": "vinyl",
                "low_e_coating": True,
                "gas_fill": "argon",
                "u_factor": 0.30,  # Manufacturer rating
                "shgc": 0.25,  # Solar heat gain coefficient
            },
            "doors": {
                "type": "insulated_steel",
                "u_factor": 0.35,
            },
        }

        # Adjust based on building type
        if design.building_type == "commercial":
            # Commercial buildings typically have better envelope performance
            envelope_data["walls"]["insulation_r_value"] = 19.0  # R-19
            envelope_data["roof"]["insulation_r_value"] = 38.0  # R-38
            envelope_data["windows"]["u_factor"] = 0.25  # Better windows

        return envelope_data

    async def _calculate_wall_r_value(
        self, wall_data: Dict, climate_zone: str
    ) -> float:
        """Calculate total wall assembly R-value."""
        # Sum R-values of all wall components
        total_r_value = (
            wall_data.get("insulation_r_value", 0)
            + wall_data.get("sheathing_r_value", 0)
            + wall_data.get("siding_r_value", 0)
            + wall_data.get("interior_finish_r_value", 0)
            + wall_data.get("air_film_r_values", 0)
        )

        # Account for thermal bridging (typically reduces effective R-value by 15-25%)
        thermal_bridging_factor = 0.8  # 20% reduction
        effective_r_value = total_r_value * thermal_bridging_factor

        return effective_r_value

    async def _calculate_roof_r_value(
        self, roof_data: Dict, climate_zone: str
    ) -> float:
        """Calculate total roof assembly R-value."""
        # Sum R-values of all roof components
        total_r_value = (
            roof_data.get("insulation_r_value", 0)
            + roof_data.get("sheathing_r_value", 0)
            + roof_data.get("roofing_r_value", 0)
            + roof_data.get("air_film_r_values", 0)
        )

        # Account for thermal bridging (less significant in roofs)
        thermal_bridging_factor = 0.9  # 10% reduction
        effective_r_value = total_r_value * thermal_bridging_factor

        return effective_r_value

    async def _calculate_window_u_factor(
        self, window_data: Dict, climate_zone: str
    ) -> float:
        """Calculate window assembly U-factor."""
        # Use manufacturer U-factor if available
        base_u_factor = window_data.get("u_factor", 0.50)  # Default single pane

        # Adjust for frame type
        frame_type = window_data.get("frame_type", "aluminum")
        if frame_type == "vinyl":
            frame_adjustment = 0.95  # 5% improvement
        elif frame_type == "wood":
            frame_adjustment = 0.90  # 10% improvement
        elif frame_type == "fiberglass":
            frame_adjustment = 0.85  # 15% improvement
        else:  # aluminum
            frame_adjustment = 1.0  # No improvement

        # Adjust for low-E coating
        low_e_adjustment = 0.85 if window_data.get("low_e_coating", False) else 1.0

        # Adjust for gas fill
        gas_fill = window_data.get("gas_fill", "air")
        if gas_fill == "argon":
            gas_adjustment = 0.90  # 10% improvement
        elif gas_fill == "krypton":
            gas_adjustment = 0.85  # 15% improvement
        else:  # air
            gas_adjustment = 1.0  # No improvement

        effective_u_factor = (
            base_u_factor * frame_adjustment * low_e_adjustment * gas_adjustment
        )

        return effective_u_factor

    async def _calculate_infiltration_rate(
        self, envelope_data: Dict, building_parameters: BuildingParameters
    ) -> float:
        """Calculate air infiltration rate in ACH (air changes per hour)."""
        # Base infiltration rate depends on construction quality
        # Typical values: 0.1-0.3 ACH for tight construction, 0.5-1.0 ACH for average

        # Assume average construction quality
        base_infiltration = 0.35  # ACH at 50 Pa

        # Adjust for building age (newer buildings are typically tighter)
        # This would be based on design metadata in a real implementation
        age_factor = 1.0  # Assume new construction

        # Adjust for building height (taller buildings have more stack effect)
        height_factor = 1.0 + (building_parameters.number_of_floors - 1) * 0.05

        # Calculate natural infiltration rate (typically 1/20 of blower door test)
        natural_infiltration = base_infiltration * age_factor * height_factor / 20

        return natural_infiltration

    def _get_climate_data(self, climate_zone: str) -> Dict:
        """Get climate data for the specified zone."""
        # Climate zone data (simplified)
        climate_zones = {
            "1A": {"hdd": 500, "cdd": 5000, "name": "Very Hot-Humid"},
            "2A": {"hdd": 1500, "cdd": 3500, "name": "Hot-Humid"},
            "2B": {"hdd": 1400, "cdd": 3000, "name": "Hot-Dry"},
            "3A": {"hdd": 2500, "cdd": 2500, "name": "Warm-Humid"},
            "3B": {"hdd": 2400, "cdd": 2000, "name": "Warm-Dry"},
            "3C": {"hdd": 2000, "cdd": 500, "name": "Warm-Marine"},
            "4A": {"hdd": 4000, "cdd": 1500, "name": "Mixed-Humid"},
            "4B": {"hdd": 3800, "cdd": 1200, "name": "Mixed-Dry"},
            "4C": {"hdd": 3500, "cdd": 300, "name": "Mixed-Marine"},
            "5A": {"hdd": 5500, "cdd": 1000, "name": "Cool-Humid"},
            "5B": {"hdd": 5200, "cdd": 800, "name": "Cool-Dry"},
            "6A": {"hdd": 7000, "cdd": 600, "name": "Cold-Humid"},
            "6B": {"hdd": 6800, "cdd": 400, "name": "Cold-Dry"},
            "7": {"hdd": 9000, "cdd": 300, "name": "Very Cold"},
            "8": {"hdd": 12000, "cdd": 100, "name": "Subarctic"},
        }

        return climate_zones.get(climate_zone, climate_zones["4A"])  # Default to 4A

    async def _calculate_heating_energy(
        self,
        building_parameters: BuildingParameters,
        envelope_metrics: EnvelopeMetrics,
        climate_data: Dict,
    ) -> float:
        """Calculate annual heating energy consumption."""
        # Simplified heating energy calculation
        # Real implementation would use detailed building energy modeling

        # Base heating load (Btu/hr/sq ft) based on envelope performance
        base_heating_load = 25.0  # Btu/hr/sq ft for average building

        # Adjust for envelope performance
        envelope_factor = (
            20.0 / envelope_metrics.wall_r_value
        )  # Better insulation = lower load
        infiltration_factor = (
            envelope_metrics.infiltration_rate / 0.35
        )  # Higher infiltration = higher load

        adjusted_heating_load = (
            base_heating_load * envelope_factor * infiltration_factor
        )

        # Calculate annual heating energy
        heating_degree_days = climate_data["hdd"]
        heating_hours = heating_degree_days * 24  # Approximate heating hours

        # Convert to kWh (assuming heat pump with COP of 3.0)
        cop = 3.0  # Coefficient of performance
        heating_btuh = adjusted_heating_load * building_parameters.total_area
        heating_kwh = (heating_btuh * heating_hours) / (3412 * cop)  # 3412 Btu/kWh

        return max(0, heating_kwh)

    async def _calculate_cooling_energy(
        self,
        building_parameters: BuildingParameters,
        envelope_metrics: EnvelopeMetrics,
        climate_data: Dict,
    ) -> float:
        """Calculate annual cooling energy consumption."""
        # Simplified cooling energy calculation

        # Base cooling load (Btu/hr/sq ft) based on envelope performance
        base_cooling_load = 30.0  # Btu/hr/sq ft for average building

        # Adjust for envelope performance
        window_factor = (
            envelope_metrics.window_u_factor / 0.30
        )  # Better windows = lower load
        infiltration_factor = envelope_metrics.infiltration_rate / 0.35

        adjusted_cooling_load = base_cooling_load * window_factor * infiltration_factor

        # Calculate annual cooling energy
        cooling_degree_days = climate_data["cdd"]
        cooling_hours = cooling_degree_days * 24 / 65  # Approximate cooling hours

        # Convert to kWh (assuming AC with SEER 14)
        seer = 14.0  # Seasonal Energy Efficiency Ratio
        cooling_btuh = adjusted_cooling_load * building_parameters.total_area
        cooling_kwh = (cooling_btuh * cooling_hours) / (seer * 1000)  # SEER is Btu/Wh

        return max(0, cooling_kwh)

    async def _calculate_lighting_energy(
        self, building_parameters: BuildingParameters, building_type: str
    ) -> float:
        """Calculate annual lighting energy consumption."""
        # Lighting power density (W/sq ft) by building type
        lighting_densities = {
            "residential": 1.0,  # W/sq ft
            "commercial": 1.2,  # W/sq ft
            "office": 1.1,  # W/sq ft
            "retail": 1.5,  # W/sq ft
            "warehouse": 0.8,  # W/sq ft
            "industrial": 1.3,  # W/sq ft
        }

        lighting_density = lighting_densities.get(building_type, 1.1)

        # Operating hours per year by building type
        operating_hours = {
            "residential": 3000,  # hours/year
            "commercial": 3500,  # hours/year
            "office": 3000,  # hours/year
            "retail": 4000,  # hours/year
            "warehouse": 2500,  # hours/year
            "industrial": 4500,  # hours/year
        }

        hours = operating_hours.get(building_type, 3000)

        # Calculate lighting energy
        lighting_power = lighting_density * building_parameters.total_area  # Watts
        lighting_kwh = (lighting_power * hours) / 1000  # Convert to kWh

        return lighting_kwh

    async def _calculate_equipment_energy(
        self, building_parameters: BuildingParameters, building_type: str
    ) -> float:
        """Calculate annual equipment energy consumption."""
        # Equipment power density (W/sq ft) by building type
        equipment_densities = {
            "residential": 2.0,  # W/sq ft (appliances, electronics)
            "commercial": 1.5,  # W/sq ft
            "office": 1.0,  # W/sq ft (computers, printers)
            "retail": 0.8,  # W/sq ft
            "warehouse": 0.5,  # W/sq ft
            "industrial": 3.0,  # W/sq ft (machinery)
        }

        equipment_density = equipment_densities.get(building_type, 1.0)

        # Operating hours per year (typically less than lighting)
        operating_hours = {
            "residential": 4000,  # hours/year
            "commercial": 3000,  # hours/year
            "office": 2500,  # hours/year
            "retail": 3500,  # hours/year
            "warehouse": 2000,  # hours/year
            "industrial": 4000,  # hours/year
        }

        hours = operating_hours.get(building_type, 2500)

        # Calculate equipment energy
        equipment_power = equipment_density * building_parameters.total_area  # Watts
        equipment_kwh = (equipment_power * hours) / 1000  # Convert to kWh

        return equipment_kwh

    async def _generate_efficiency_recommendations(
        self,
        envelope_metrics: EnvelopeMetrics,
        energy_estimate: EnergyEstimate,
        standards: List[str],
    ) -> List[EfficiencyRecommendation]:
        """Generate energy efficiency recommendations."""
        recommendations = []

        # Wall insulation recommendation
        if envelope_metrics.wall_r_value < 15.0:
            savings_kwh = energy_estimate.heating_kwh * 0.15  # 15% heating savings
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="Envelope",
                    description="Increase wall insulation to R-19 or higher",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("3000"),
                )
            )

        # Roof insulation recommendation
        if envelope_metrics.roof_r_value < 30.0:
            savings_kwh = energy_estimate.heating_kwh * 0.20  # 20% heating savings
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="Envelope",
                    description="Increase roof insulation to R-38 or higher",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("2500"),
                )
            )

        # Window upgrade recommendation
        if envelope_metrics.window_u_factor > 0.30:
            savings_kwh = (
                energy_estimate.heating_kwh + energy_estimate.cooling_kwh
            ) * 0.12
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="Envelope",
                    description="Upgrade to high-performance windows (U-factor ≤ 0.25)",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("8000"),
                )
            )

        # Air sealing recommendation
        if envelope_metrics.infiltration_rate > 0.25:
            savings_kwh = (
                energy_estimate.heating_kwh + energy_estimate.cooling_kwh
            ) * 0.10
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="Envelope",
                    description="Improve air sealing to reduce infiltration",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("1500"),
                )
            )

        # LED lighting recommendation
        if energy_estimate.lighting_kwh > 5000:  # High lighting energy use
            savings_kwh = energy_estimate.lighting_kwh * 0.50  # 50% lighting savings
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="Lighting",
                    description="Upgrade to LED lighting with occupancy sensors",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("4000"),
                )
            )

        # HVAC upgrade recommendation
        total_hvac_kwh = energy_estimate.heating_kwh + energy_estimate.cooling_kwh
        if total_hvac_kwh > 15000:  # High HVAC energy use
            savings_kwh = total_hvac_kwh * 0.25  # 25% HVAC savings
            savings_cost = Decimal(str(savings_kwh)) * Decimal("0.12")
            recommendations.append(
                EfficiencyRecommendation(
                    category="HVAC",
                    description="Upgrade to high-efficiency heat pump system",
                    estimated_savings_kwh=savings_kwh,
                    estimated_cost_savings=savings_cost,
                    implementation_cost=Decimal("12000"),
                )
            )

        return recommendations

    def _build_energy_response(
        self, energy_analysis: EnergyAnalysis
    ) -> EnergyAnalysisResponse:
        """
        Build EnergyAnalysisResponse from EnergyAnalysis model.

        Args:
            energy_analysis: EnergyAnalysis model instance

        Returns:
            EnergyAnalysisResponse schema
        """
        # Convert envelope performance from JSON to EnvelopeMetrics object
        envelope_performance = None
        if energy_analysis.envelope_performance:
            envelope_performance = EnvelopeMetrics(
                **energy_analysis.envelope_performance
            )

        # Convert energy consumption from JSON to EnergyEstimate object
        energy_consumption = None
        if energy_analysis.energy_consumption:
            energy_consumption = EnergyEstimate(**energy_analysis.energy_consumption)

        # Convert recommendations from JSON to EfficiencyRecommendation objects
        recommendations = []
        for r_data in energy_analysis.recommendations:
            recommendations.append(EfficiencyRecommendation(**r_data))

        return EnergyAnalysisResponse(
            id=UUID(energy_analysis.id),
            design_id=UUID(energy_analysis.design_id),
            design_version=energy_analysis.design_version,
            standards=energy_analysis.standards,
            climate_zone=energy_analysis.climate_zone,
            status=CheckStatus(energy_analysis.status),
            envelope_performance=envelope_performance,
            energy_consumption=energy_consumption,
            recommendations=recommendations,
            certificate_url=energy_analysis.certificate_url,
            started_at=energy_analysis.started_at,
            completed_at=energy_analysis.completed_at,
        )
