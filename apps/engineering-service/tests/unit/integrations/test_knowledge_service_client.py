"""Unit tests for KnowledgeServiceClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.integrations.knowledge_service_client import KnowledgeServiceClient


@pytest.fixture
def client():
    """Create KnowledgeServiceClient instance."""
    return KnowledgeServiceClient(
        base_url="http://localhost:8002",
        timeout=30.0,
        max_retries=3,
    )


@pytest.mark.asyncio
async def test_get_code_requirements_success(client):
    """Test successful code requirements retrieval."""
    expected_data = {
        "code_type": "structural",
        "jurisdiction": "California",
        "version": "IBC 2021",
        "requirements": {
            "seismic_design_category": "D",
            "wind_speed": 110,
        },
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_code_requirements(
            code_type="structural",
            jurisdiction="California",
        )

        assert result == expected_data
        assert result["code_type"] == "structural"
        mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_code_requirements_with_version(client):
    """Test code requirements retrieval with specific version."""
    expected_data = {
        "code_type": "mep",
        "jurisdiction": "New York",
        "version": "NEC 2020",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_code_requirements(
            code_type="mep",
            jurisdiction="New York",
            version="NEC 2020",
        )

        assert result == expected_data
        assert result["version"] == "NEC 2020"


@pytest.mark.asyncio
async def test_search_code_sections_success(client):
    """Test successful code sections search."""
    expected_data = {
        "results": [
            {
                "section": "1605.2",
                "title": "Load Combinations",
                "content": "Basic load combinations...",
            },
            {
                "section": "1605.3",
                "title": "Strength Design",
                "content": "Strength design requirements...",
            },
        ]
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.search_code_sections(
            code_type="structural",
            search_query="load combinations",
        )

        assert len(result) == 2
        assert result[0]["section"] == "1605.2"


@pytest.mark.asyncio
async def test_get_engineering_formula_success(client):
    """Test successful engineering formula retrieval."""
    expected_data = {
        "name": "beam_deflection",
        "formula": "δ = (5 * w * L^4) / (384 * E * I)",
        "variables": {
            "δ": "deflection",
            "w": "uniform load",
            "L": "span length",
            "E": "modulus of elasticity",
            "I": "moment of inertia",
        },
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_engineering_formula(
            formula_name="beam_deflection",
            discipline="structural",
        )

        assert result == expected_data
        assert result["name"] == "beam_deflection"


@pytest.mark.asyncio
async def test_search_formulas_success(client):
    """Test successful formulas search."""
    expected_data = {
        "results": [
            {
                "name": "hvac_cooling_load",
                "formula": "Q = m * Cp * ΔT",
            },
            {
                "name": "hvac_heating_load",
                "formula": "Q = U * A * ΔT",
            },
        ]
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.search_formulas(
            query="hvac load",
            discipline="mep",
            limit=10,
        )

        assert len(result) == 2
        assert "hvac" in result[0]["name"]


@pytest.mark.asyncio
async def test_get_material_properties_success(client):
    """Test successful material properties retrieval."""
    expected_data = {
        "name": "A992 Steel",
        "type": "steel",
        "properties": {
            "yield_strength": 50000,  # psi
            "tensile_strength": 65000,  # psi
            "modulus_of_elasticity": 29000000,  # psi
        },
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_material_properties(
            material_name="A992 Steel",
            material_type="steel",
        )

        assert result == expected_data
        assert result["name"] == "A992 Steel"


@pytest.mark.asyncio
async def test_get_standard_reference_success(client):
    """Test successful standard reference retrieval."""
    expected_data = {
        "name": "ASCE 7-16",
        "title": "Minimum Design Loads for Buildings",
        "year": 2016,
        "organization": "ASCE",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_standard_reference(standard_name="ASCE 7-16")

        assert result == expected_data
        assert result["name"] == "ASCE 7-16"


@pytest.mark.asyncio
async def test_http_error_handling(client):
    """Test HTTP error handling."""
    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Not found")

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        with pytest.raises(httpx.HTTPError):
            await client.get_code_requirements(
                code_type="structural",
                jurisdiction="California",
            )


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    async with KnowledgeServiceClient(
        base_url="http://localhost:8002",
    ) as client:
        assert client._client is not None

    # Client should be closed after exiting context
    assert client._client is None or client._client.is_closed


@pytest.mark.asyncio
async def test_close(client):
    """Test client close method."""
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    client._client = mock_client

    await client.close()

    mock_client.aclose.assert_called_once()
    assert client._client is None


@pytest.mark.asyncio
async def test_get_client_lazy_initialization(client):
    """Test lazy initialization of HTTP client."""
    assert client._client is None

    http_client = client._get_client()

    assert http_client is not None
    assert client._client is not None


@pytest.mark.asyncio
async def test_search_with_jurisdiction_filter(client):
    """Test code section search with jurisdiction filter."""
    expected_data = {
        "results": [
            {
                "section": "1605.2",
                "jurisdiction": "California",
            }
        ]
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.search_code_sections(
            code_type="structural",
            search_query="load",
            jurisdiction="California",
        )

        assert len(result) == 1
        assert result[0]["jurisdiction"] == "California"
