"""Material service for construction material specifications."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import (MaterialSpecificationRequest,
                                         MaterialSpecificationResponse,
                                         VendorInfo)
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.vendor_service_client import (MaterialQuery,
                                                      VendorServiceClient)
from src.models.material_specification import MaterialSpecification
from src.repositories.design_repository import DesignRepository
from src.repositories.material_specification_repository import \
    MaterialSpecificationRepository

logger = logging.getLogger(__name__)


class MaterialService:
    """
    Service for managing construction material specifications.

    Handles material specification creation, vendor integration,
    and material search with pricing information.
    """

    def __init__(
        self,
        material_repository: MaterialSpecificationRepository,
        design_repository: DesignRepository,
        vendor_client: VendorServiceClient,
    ):
        """
        Initialize MaterialService.

        Args:
            material_repository: Repository for material data access
            design_repository: Repository for design data access
            vendor_client: Client for vendor service integration
        """
        self.material_repository = material_repository
        self.design_repository = design_repository
        self.vendor_client = vendor_client

    async def add_material(
        self,
        design_id: UUID,
        data: MaterialSpecificationRequest,
    ) -> MaterialSpecification:
        """
        Add material specification to design with validation.

        Validates design exists, creates material specification,
        and optionally integrates with vendor service for pricing.

        Args:
            design_id: Design ID to add material to
            data: Material specification request data

        Returns:
            Created MaterialSpecification instance

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If material data is invalid
        """
        # Validate design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot add material to deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Validate required material properties
        self._validate_material_properties(data)

        # Handle both enum and string values for category
        category_value = (
            data.category.value if hasattr(data.category, "value") else data.category
        )

        # Create material specification
        material = MaterialSpecification(
            id=str(uuid4()),
            design_id=str(design_id),
            category=category_value,
            material_type=data.properties.type,
            properties=data.properties.model_dump(),
            design_elements=[str(elem_id) for elem_id in data.design_elements],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Try to get vendor information
        try:
            vendor_materials = await self._search_vendor_materials(data)
            if vendor_materials:
                # Use first matching material
                vendor_material = vendor_materials[0]
                material.vendor_material_id = str(vendor_material.material_id)
                material.vendor_info = {
                    "vendor_id": str(vendor_material.vendor_id),
                    "vendor_name": vendor_material.vendor_name,
                    "product_code": vendor_material.name,
                    "availability": "in_stock"
                    if vendor_material.in_stock
                    else "out_of_stock",
                    "lead_time_days": vendor_material.lead_time_days,
                }
                material.cost_estimate = vendor_material.price
        except Exception as e:
            logger.warning(f"Failed to get vendor information for material: {e}")
            # Continue without vendor info

        # Save material
        material = await self.material_repository.create(material)

        logger.info(
            f"Added material {material.id} to design {design_id} "
            f"(category: {material.category}, type: {material.material_type})"
        )

        return material

    async def list_materials_for_design(
        self,
        design_id: UUID,
        category: Optional[str] = None,
    ) -> List[MaterialSpecification]:
        """
        List all material specifications for a design.

        Args:
            design_id: Design ID to list materials for
            category: Optional category filter

        Returns:
            List of MaterialSpecification instances

        Raises:
            NotFoundError: If design doesn't exist
        """
        # Validate design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Get materials for design
        materials = await self.material_repository.list_by_design(
            str(design_id), category
        )

        logger.debug(f"Found {len(materials)} materials for design {design_id}")

        return materials

    async def search_materials(
        self,
        query: str,
        category: Optional[str] = None,
        material_type: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock: Optional[bool] = None,
    ) -> List[MaterialSpecificationResponse]:
        """
        Search for materials with Vendor Service integration.

        Searches vendor catalog for materials matching criteria
        and returns results with pricing and availability.

        Args:
            query: Search query string
            category: Optional material category filter
            material_type: Optional material type filter
            min_price: Optional minimum price filter
            max_price: Optional maximum price filter
            in_stock: Optional stock availability filter

        Returns:
            List of MaterialSpecificationResponse with vendor info

        Raises:
            ValidationError: If search parameters are invalid
        """
        if not query.strip():
            raise ValidationError(
                "Search query cannot be empty",
                details={"query": query},
            )

        try:
            # Create vendor search query
            vendor_query = MaterialQuery(
                query=query,
                category=category,
                material_type=material_type,
                min_price=min_price,
                max_price=max_price,
                in_stock=in_stock,
            )

            # Search vendor catalog
            vendor_materials = await self.vendor_client.search_materials(vendor_query)

            # Convert to response format
            results = []
            for vendor_material in vendor_materials:
                # Create material specification response
                material_response = MaterialSpecificationResponse(
                    id=vendor_material.material_id,
                    design_id=UUID(
                        "00000000-0000-0000-0000-000000000000"
                    ),  # Placeholder
                    category=vendor_material.category,
                    properties={
                        "type": vendor_material.material_type,
                        "properties": vendor_material.properties,
                    },
                    vendor_info=VendorInfo(
                        vendor_id=vendor_material.vendor_id,
                        vendor_name=vendor_material.vendor_name,
                        product_code=vendor_material.name,
                        availability="in_stock"
                        if vendor_material.in_stock
                        else "out_of_stock",
                        lead_time_days=vendor_material.lead_time_days,
                    ),
                    cost_estimate=vendor_material.price,
                    design_elements=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                results.append(material_response)

            logger.info(f"Found {len(results)} materials for query: {query}")

            return results

        except Exception as e:
            logger.error(f"Failed to search materials with query '{query}': {e}")
            raise ValidationError(
                f"Material search failed: {str(e)}",
                details={"query": query, "error": str(e)},
            )

    async def get_vendor_info(self, material_id: UUID) -> VendorInfo:
        """
        Retrieve vendor information from Vendor Service.

        Gets detailed supplier information including contact details,
        pricing, and availability for a specific material.

        Args:
            material_id: Material ID to get vendor info for

        Returns:
            VendorInfo with supplier details

        Raises:
            NotFoundError: If material not found in vendor catalog
        """
        try:
            supplier_info = await self.vendor_client.get_supplier_info(material_id)

            vendor_info = VendorInfo(
                vendor_id=supplier_info.vendor_id,
                vendor_name=supplier_info.vendor_name,
                product_code=None,  # Not provided by supplier info
                availability=None,  # Not provided by supplier info
                lead_time_days=None,  # Not provided by supplier info
            )

            logger.debug(f"Retrieved vendor info for material {material_id}")

            return vendor_info

        except Exception as e:
            logger.error(f"Failed to get vendor info for material {material_id}: {e}")
            raise NotFoundError(
                f"Vendor information not found for material {material_id}",
                details={"material_id": str(material_id), "error": str(e)},
            )

    async def update_material_pricing(self, material_id: UUID) -> MaterialSpecification:
        """
        Update material pricing from Vendor Service.

        Refreshes pricing and availability information for a material
        specification from the vendor catalog.

        Args:
            material_id: Material specification ID to update

        Returns:
            Updated MaterialSpecification with current pricing

        Raises:
            NotFoundError: If material specification doesn't exist
        """
        # Get material specification
        material = await self.material_repository.get(str(material_id))
        if material is None:
            raise NotFoundError(
                f"Material specification {material_id} not found",
                details={"material_id": str(material_id)},
            )

        # Check if material has vendor information
        if not material.vendor_material_id:
            raise ValidationError(
                f"Material {material_id} has no vendor information to update",
                details={"material_id": str(material_id)},
            )

        try:
            # Get updated availability and pricing
            availability_info = await self.vendor_client.check_availability(
                UUID(material.vendor_material_id), Decimal("1")
            )

            # Update material with new pricing
            update_data = {
                "cost_estimate": availability_info.price,
                "updated_at": datetime.utcnow(),
            }

            # Update vendor info
            if material.vendor_info:
                vendor_info = material.vendor_info.copy()
                vendor_info.update(
                    {
                        "availability": "in_stock"
                        if availability_info.in_stock
                        else "out_of_stock",
                        "lead_time_days": availability_info.lead_time_days,
                    }
                )
                update_data["vendor_info"] = vendor_info

            # Update in database
            material = await self.material_repository.update(
                str(material_id), **update_data
            )

            logger.info(f"Updated pricing for material {material_id}")

            return material

        except Exception as e:
            logger.error(f"Failed to update pricing for material {material_id}: {e}")
            raise ValidationError(
                f"Failed to update material pricing: {str(e)}",
                details={"material_id": str(material_id), "error": str(e)},
            )

    def _validate_material_properties(self, data: MaterialSpecificationRequest) -> None:
        """
        Validate material properties for required fields.

        Args:
            data: Material specification request data

        Raises:
            ValidationError: If required properties are missing
        """
        properties = data.properties

        # Check required properties
        if not properties.type:
            raise ValidationError(
                "Material type is required",
                details={"field": "properties.type"},
            )

        # Category-specific validation
        category_value = (
            data.category.value if hasattr(data.category, "value") else data.category
        )

        if category_value == "structural":
            # Structural materials should have grade and strength properties
            if not properties.grade:
                logger.warning(
                    f"Structural material {properties.type} missing grade specification"
                )

        elif category_value == "finishes":
            # Finish materials should have finish specification
            if not properties.finish:
                logger.warning(
                    f"Finish material {properties.type} missing finish specification"
                )

        # Validate design elements are UUIDs
        for elem_id in data.design_elements:
            try:
                UUID(str(elem_id))
            except ValueError:
                raise ValidationError(
                    f"Invalid design element ID: {elem_id}",
                    details={"field": "design_elements", "value": str(elem_id)},
                )

    async def _search_vendor_materials(
        self, data: MaterialSpecificationRequest
    ) -> List:
        """
        Search vendor materials based on material specification.

        Args:
            data: Material specification request data

        Returns:
            List of matching vendor materials
        """
        # Create search query from material properties
        query_terms = [data.properties.type]
        if data.properties.grade:
            query_terms.append(data.properties.grade)

        query = " ".join(query_terms)

        category_value = (
            data.category.value if hasattr(data.category, "value") else data.category
        )

        vendor_query = MaterialQuery(
            query=query,
            category=category_value,
            material_type=data.properties.type,
        )

        return await self.vendor_client.search_materials(vendor_query)
