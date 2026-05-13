"""Knowledge Service Client for retrieving engineering codes and standards."""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class KnowledgeServiceClient:
    """Client for interacting with Knowledge Service.

    Provides methods to retrieve engineering codes, standards,
    formulas, and technical references.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize Knowledge Service client.

        Args:
            base_url: Base URL of Knowledge Service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def get_code_requirements(
        self,
        code_type: str,
        jurisdiction: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve code requirements from Knowledge Service.

        Args:
            code_type: Type of code (structural, mep, energy, fire)
            jurisdiction: Jurisdiction for code requirements
            version: Optional specific code version

        Returns:
            Dictionary containing code requirements

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching {code_type} code requirements for {jurisdiction}")

        client = self._get_client()

        params = {
            "code_type": code_type,
            "jurisdiction": jurisdiction,
        }
        if version:
            params["version"] = version

        try:
            response = await client.get(
                "/api/v1/codes/requirements",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(
                f"Retrieved code requirements: {data.get('version', 'unknown')}"
            )

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch code requirements: {e}")
            raise

    async def search_code_sections(
        self,
        code_type: str,
        search_query: str,
        jurisdiction: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for specific code sections.

        Args:
            code_type: Type of code to search
            search_query: Search query string
            jurisdiction: Optional jurisdiction filter

        Returns:
            List of matching code sections

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Searching {code_type} code sections: {search_query}")

        client = self._get_client()

        params = {
            "code_type": code_type,
            "query": search_query,
        }
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        try:
            response = await client.get(
                "/api/v1/codes/search",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            logger.debug(f"Found {len(results)} matching code sections")

            return results

        except httpx.HTTPError as e:
            logger.error(f"Failed to search code sections: {e}")
            raise

    async def get_engineering_formula(
        self,
        formula_name: str,
        discipline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve engineering formula by name.

        Args:
            formula_name: Name of the formula
            discipline: Optional discipline filter (structural, mep, civil)

        Returns:
            Dictionary containing formula details

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching engineering formula: {formula_name}")

        client = self._get_client()

        params = {"name": formula_name}
        if discipline:
            params["discipline"] = discipline

        try:
            response = await client.get(
                "/api/v1/formulas",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved formula: {data.get('name', 'unknown')}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch formula: {e}")
            raise

    async def search_formulas(
        self,
        query: str,
        discipline: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search engineering formulas.

        Args:
            query: Search query string
            discipline: Optional discipline filter
            limit: Maximum number of results

        Returns:
            List of matching formulas

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Searching formulas: {query}")

        client = self._get_client()

        params = {
            "query": query,
            "limit": limit,
        }
        if discipline:
            params["discipline"] = discipline

        try:
            response = await client.get(
                "/api/v1/formulas/search",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            logger.debug(f"Found {len(results)} matching formulas")

            return results

        except httpx.HTTPError as e:
            logger.error(f"Failed to search formulas: {e}")
            raise

    async def get_material_properties(
        self,
        material_name: str,
        material_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve material properties.

        Args:
            material_name: Name of the material
            material_type: Optional material type (steel, concrete, wood, etc.)

        Returns:
            Dictionary containing material properties

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching material properties: {material_name}")

        client = self._get_client()

        params = {"name": material_name}
        if material_type:
            params["type"] = material_type

        try:
            response = await client.get(
                "/api/v1/materials",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved material: {data.get('name', 'unknown')}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch material properties: {e}")
            raise

    async def get_standard_reference(
        self,
        standard_name: str,
    ) -> Dict[str, Any]:
        """Retrieve engineering standard reference.

        Args:
            standard_name: Name of the standard (e.g., "ASCE 7-16", "NEC 2020")

        Returns:
            Dictionary containing standard details

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.info(f"Fetching standard reference: {standard_name}")

        client = self._get_client()

        try:
            response = await client.get(
                f"/api/v1/standards/{standard_name}",
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Retrieved standard: {data.get('name', 'unknown')}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch standard reference: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
