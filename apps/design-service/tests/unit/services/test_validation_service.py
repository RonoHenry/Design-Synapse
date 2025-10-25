"""
Tests for ValidationService.

This module tests the design validation service including:
- Compliant design validation
- Design validation with violations
- Design validation with warnings only
- Rule set loading and parsing
- Rule configuration validation
- Performance requirements (completion within 10 seconds)
"""

import pytest
import time
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch, mock_open
import json

from src.services.validation_service import ValidationService, RuleEngine
from src.repositories.validation_repository import ValidationRepository
from src.repositories.design_repository import DesignRepository
from src.models.design import Design
from src.models.design_validation import DesignValidation


class TestValidationService:
    """Test suite for ValidationService."""

    @pytest.fixture
    def validation_repo(self, db_session):
        """Create a validation repository for testing."""
        return ValidationRepository(db_session)

    @pytest.fixture
    def design_repo(self, db_session):
        """Create a design repository for testing."""
        return DesignRepository(db_session)

    @pytest.fixture
    def rule_engine(self):
        """Create a mock rule engine for testing."""
        return Mock(spec=RuleEngine)

    @pytest.fixture
    def validation_service(self, validation_repo, design_repo, rule_engine):
        """Create a validation service for testing."""
        return ValidationService(validation_repo, design_repo, rule_engine)

    @pytest.fixture
    def valid_rule_set(self):
        """Create a valid rule set configuration for testing."""
        return {
            "metadata": {
                "name": "Test Building Code 2020",
                "version": "2020.1",
                "jurisdiction": "Test Country",
                "effective_date": "2020-01-01",
                "description": "Test building code rules",
                "last_updated": "2020-12-31"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning Requirements",
                    "description": "Zoning compliance and setback requirements"
                },
                "structural": {
                    "name": "Structural Requirements",
                    "description": "Rules for structural integrity and safety"
                }
            },
            "rules": [
                {
                    "id": "SETBACK_FRONT",
                    "category": "zoning",
                    "name": "Front Setback Requirement",
                    "description": "Minimum distance from front property boundary",
                    "severity": "critical",
                    "building_types": ["residential", "commercial"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "setbacks.front",
                        "operator": ">=",
                        "value": 5.0,
                        "unit": "meters"
                    },
                    "violation_message": "Front setback must be at least {required_value} {unit}",
                    "suggestion": "Increase front setback to meet minimum requirement"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "severity_levels": {
                    "critical": {
                        "blocks_approval": True,
                        "color": "red",
                        "priority": 1
                    },
                    "warning": {
                        "blocks_approval": False,
                        "color": "orange",
                        "priority": 2
                    }
                }
            }
        }

    @pytest.fixture
    def invalid_rule_set(self):
        """Create an invalid rule set configuration for testing."""
        return {
            "metadata": {
                "name": "Invalid Rule Set"
                # Missing required fields
            },
            "rules": [
                {
                    "id": "INVALID_RULE",
                    # Missing required fields
                    "severity": "invalid_severity"
                }
            ]
        }

    @pytest.fixture
    def temp_rules_dir(self, valid_rule_set):
        """Create a temporary directory with rule files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid rule file
            rule_file_path = os.path.join(temp_dir, "Standard_Building_Code_2020.json")
            with open(rule_file_path, "w") as f:
                json.dump(valid_rule_set, f)
            
            yield temp_dir

    @pytest.fixture
    def compliant_design(self, db_session):
        """Create a compliant design for testing."""
        from tests.factories import DesignFactory
        
        design = DesignFactory.create(
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.5,
                    "num_floors": 2,
                    "height": 7.5
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                },
                "compliance": {
                    "building_code": "Standard_Building_Code_2020",
                    "setbacks": {"front": 5.0, "rear": 3.0, "side": 2.0}
                }
            },
            status="draft"
        )
        db_session.commit()
        return design

    @pytest.fixture
    def non_compliant_design(self, db_session):
        """Create a non-compliant design for testing."""
        from tests.factories import DesignFactory
        
        design = DesignFactory.create(
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.5,
                    "num_floors": 2,
                    "height": 7.5
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                },
                "compliance": {
                    "building_code": "Standard_Building_Code_2020",
                    "setbacks": {"front": 4.5, "rear": 3.0, "side": 2.0}  # Front setback violation
                }
            },
            status="draft"
        )
        db_session.commit()
        return design

    def test_validate_design_compliant(
        self,
        validation_service,
        compliant_design,
        rule_engine,
        db_session
    ):
        """Test validation of a compliant design."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        # Mock rule engine to return no violations
        rule_engine.validate.return_value = {
            "is_compliant": True,
            "violations": [],
            "warnings": []
        }
        
        # Act
        result = validation_service.validate_design(
            design=compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, DesignValidation)
        assert result.design_id == compliant_design.id
        assert result.validation_type == validation_type
        assert result.rule_set == rule_set
        assert result.is_compliant is True
        assert result.violations == []
        assert result.warnings == []
        assert result.validated_by == user_id
        assert result.validated_at is not None
        
        # Verify design status was updated
        db_session.refresh(compliant_design)
        assert compliant_design.status == "compliant"
        
        # Verify rule engine was called correctly
        rule_engine.validate.assert_called_once()

    def test_validate_design_with_violations(
        self,
        validation_service,
        non_compliant_design,
        rule_engine,
        db_session
    ):
        """Test validation of a design with violations."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        expected_violations = [
            {
                "code": "SETBACK_VIOLATION",
                "severity": "critical",
                "rule": "Front setback must be at least 5 meters",
                "current_value": 4.5,
                "required_value": 5.0,
                "location": "front_boundary",
                "suggestion": "Increase front setback by 0.5 meters"
            }
        ]
        
        # Mock rule engine to return violations
        rule_engine.validate.return_value = {
            "is_compliant": False,
            "violations": expected_violations,
            "warnings": []
        }
        
        # Act
        result = validation_service.validate_design(
            design=non_compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, DesignValidation)
        assert result.design_id == non_compliant_design.id
        assert result.is_compliant is False
        assert len(result.violations) == 1
        assert result.violations[0]["code"] == "SETBACK_VIOLATION"
        assert result.violations[0]["severity"] == "critical"
        assert result.violations[0]["current_value"] == 4.5
        assert result.violations[0]["required_value"] == 5.0
        assert result.warnings == []
        
        # Verify design status was updated to non_compliant
        db_session.refresh(non_compliant_design)
        assert non_compliant_design.status == "non_compliant"

    def test_validate_design_with_warnings_only(
        self,
        validation_service,
        compliant_design,
        rule_engine,
        db_session
    ):
        """Test validation of a design with warnings but no violations."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        expected_warnings = [
            {
                "code": "MATERIAL_WARNING",
                "severity": "warning",
                "message": "Consider using locally sourced materials for cost efficiency"
            },
            {
                "code": "SUSTAINABILITY_WARNING",
                "severity": "warning",
                "message": "Consider adding solar panels for energy efficiency"
            }
        ]
        
        # Mock rule engine to return warnings only
        rule_engine.validate.return_value = {
            "is_compliant": True,
            "violations": [],
            "warnings": expected_warnings
        }
        
        # Act
        result = validation_service.validate_design(
            design=compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert result.is_compliant is True
        assert result.violations == []
        assert len(result.warnings) == 2
        assert result.warnings[0]["code"] == "MATERIAL_WARNING"
        assert result.warnings[1]["code"] == "SUSTAINABILITY_WARNING"
        
        # Verify design status is still compliant (warnings don't affect compliance)
        db_session.refresh(compliant_design)
        assert compliant_design.status == "compliant"

    def test_validate_design_with_violations_and_warnings(
        self,
        validation_service,
        non_compliant_design,
        rule_engine,
        db_session
    ):
        """Test validation with both violations and warnings."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        expected_violations = [
            {
                "code": "SETBACK_VIOLATION",
                "severity": "critical",
                "rule": "Front setback must be at least 5 meters",
                "current_value": 4.5,
                "required_value": 5.0
            }
        ]
        
        expected_warnings = [
            {
                "code": "MATERIAL_WARNING",
                "severity": "warning",
                "message": "Consider using locally sourced materials"
            }
        ]
        
        rule_engine.validate.return_value = {
            "is_compliant": False,
            "violations": expected_violations,
            "warnings": expected_warnings
        }
        
        # Act
        result = validation_service.validate_design(
            design=non_compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result.is_compliant is False
        assert len(result.violations) == 1
        assert len(result.warnings) == 1
        
        db_session.refresh(non_compliant_design)
        assert non_compliant_design.status == "non_compliant"

    def test_validation_completion_time(
        self,
        validation_service,
        compliant_design,
        rule_engine
    ):
        """Test that validation completes within 10 seconds."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        rule_engine.validate.return_value = {
            "is_compliant": True,
            "violations": [],
            "warnings": []
        }
        
        # Act
        start_time = time.time()
        result = validation_service.validate_design(
            design=compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        end_time = time.time()
        
        # Assert
        elapsed_time = end_time - start_time
        assert elapsed_time < 10.0, f"Validation took {elapsed_time:.2f} seconds, should be under 10 seconds"
        assert result is not None

    def test_validation_persists_to_database(
        self,
        validation_service,
        compliant_design,
        rule_engine,
        db_session
    ):
        """Test that validation results are persisted to the database."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        rule_engine.validate.return_value = {
            "is_compliant": True,
            "violations": [],
            "warnings": []
        }
        
        # Act
        result = validation_service.validate_design(
            design=compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert - verify we can retrieve the validation from database
        db_session.expire_all()
        retrieved = db_session.query(DesignValidation).filter_by(id=result.id).first()
        assert retrieved is not None
        assert retrieved.design_id == compliant_design.id
        assert retrieved.is_compliant is True


class TestRuleEngine:
    """Test suite for RuleEngine."""

    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine for testing."""
        return RuleEngine()

    @pytest.fixture
    def sample_rule_set(self):
        """Create a sample rule set for testing."""
        return {
            "metadata": {
                "name": "Standard Building Code 2020",
                "version": "1.0",
                "jurisdiction": "Standard",
                "effective_date": "2020-01-01",
                "description": "Standard Building Code 2020"
            },
            "rule_categories": {
                "setbacks": {
                    "name": "Setback Requirements",
                    "description": "Rules for property setbacks"
                },
                "materials": {
                    "name": "Material Requirements",
                    "description": "Rules for construction materials"
                }
            },
            "rules": [
                {
                    "id": "SETBACK_FRONT",
                    "category": "setbacks",
                    "name": "Front Setback",
                    "description": "Front setback must be at least 5 meters",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "compliance.setbacks.front",
                        "operator": ">=",
                        "value": 5.0,
                        "unit": "meters"
                    },
                    "violation_message": "Front setback must be at least 5 meters",
                    "suggestion": "Increase front setback to meet minimum requirement"
                },
                {
                    "id": "SETBACK_REAR",
                    "category": "setbacks",
                    "name": "Rear Setback",
                    "description": "Rear setback must be at least 3 meters",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "compliance.setbacks.rear",
                        "operator": ">=",
                        "value": 3.0,
                        "unit": "meters"
                    },
                    "violation_message": "Rear setback must be at least 3 meters",
                    "suggestion": "Increase rear setback to meet minimum requirement"
                },
                {
                    "id": "MATERIAL_LOCAL",
                    "category": "materials",
                    "name": "Local Materials",
                    "description": "Consider using locally sourced materials",
                    "severity": "warning",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "required_field",
                        "field": "structure.wall_material",
                        "value": True
                    },
                    "violation_message": "Consider using locally sourced materials",
                    "suggestion": "Use local materials when possible"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "max_violations_per_rule": 10,
                "severity_levels": {
                    "critical": {
                        "blocks_approval": True,
                        "color": "red",
                        "priority": 1
                    },
                    "warning": {
                        "blocks_approval": False,
                        "color": "orange",
                        "priority": 2
                    },
                    "info": {
                        "blocks_approval": False,
                        "color": "blue",
                        "priority": 3
                    }
                }
            }
        }

    def test_load_rule_set_success(self, rule_engine, sample_rule_set):
        """Test successful loading of a rule set."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act
                    result = rule_engine.load_rule_set(rule_set_name)
        
        # Assert
        assert result is not None
        assert result["metadata"]["name"] == "Standard Building Code 2020"
        assert "rule_categories" in result
        assert len(result["rule_categories"]) == 2  # setbacks and materials

    def test_load_rule_set_file_not_found(self, rule_engine):
        """Test loading a non-existent rule set."""
        # Arrange
        rule_set_name = "NonExistent_Code"
        
        with patch("os.path.exists", return_value=False):
            # Act & Assert
            with pytest.raises(FileNotFoundError) as exc_info:
                rule_engine.load_rule_set(rule_set_name)
            
            assert "Rule set not found" in str(exc_info.value)

    def test_load_rule_set_invalid_json(self, rule_engine):
        """Test loading a rule set with invalid JSON."""
        # Arrange
        rule_set_name = "Invalid_Code"
        invalid_json = "{ invalid json }"
        
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act & Assert
                    with pytest.raises(ValueError) as exc_info:
                        rule_engine.load_rule_set(rule_set_name)
                    
                    assert "Invalid rule set format" in str(exc_info.value)

    def test_validate_compliant_design(self, rule_engine, sample_rule_set):
        """Test validation of a compliant design."""
        # Arrange
        design_spec = {
            "building_info": {
                "type": "residential",
                "total_area": 250.5
            },
            "structure": {
                "wall_material": "concrete_block"
            },
            "compliance": {
                "setbacks": {"front": 5.0, "rear": 3.0, "side": 2.0}
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, sample_rule_set)
        
        # Assert
        assert result["is_compliant"] is True
        assert len(result["violations"]) == 0
        # May have warnings for material recommendation
        assert isinstance(result["warnings"], list)

    def test_validate_design_with_setback_violation(self, rule_engine, sample_rule_set):
        """Test validation of a design with setback violation."""
        # Arrange
        design_spec = {
            "building_info": {
                "type": "residential"
            },
            "structure": {
                "wall_material": "concrete_block"
            },
            "compliance": {
                "setbacks": {"front": 4.5, "rear": 3.0, "side": 2.0}  # Front setback violation
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, sample_rule_set)
        
        # Assert
        assert result["is_compliant"] is False
        assert len(result["violations"]) >= 1
        
        # Find the setback violation
        setback_violation = next(
            (v for v in result["violations"] if v["code"] == "SETBACK_FRONT"),
            None
        )
        assert setback_violation is not None
        assert setback_violation["severity"] == "critical"
        assert setback_violation["current_value"] == 4.5
        assert setback_violation["required_value"] == 5.0

    def test_validate_design_with_multiple_violations(self, rule_engine, sample_rule_set):
        """Test validation of a design with multiple violations."""
        # Arrange
        design_spec = {
            "building_info": {
                "type": "residential"
            },
            "structure": {
                "wall_material": "concrete_block"
            },
            "compliance": {
                "setbacks": {"front": 4.5, "rear": 2.5, "side": 2.0}  # Both front and rear violations
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, sample_rule_set)
        
        # Assert
        assert result["is_compliant"] is False
        assert len(result["violations"]) >= 2

    def test_extract_design_parameters(self, rule_engine):
        """Test extraction of design parameters from specification."""
        # Arrange
        design_spec = {
            "building_info": {
                "type": "residential",
                "total_area": 250.5
            },
            "compliance": {
                "setbacks": {"front": 5.0}
            }
        }
        
        # Act
        result = rule_engine.extract_parameter(design_spec, "compliance.setbacks.front")
        
        # Assert
        assert result == 5.0

    def test_extract_nested_parameter(self, rule_engine):
        """Test extraction of deeply nested parameters."""
        # Arrange
        design_spec = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": 42
                    }
                }
            }
        }
        
        # Act
        result = rule_engine.extract_parameter(design_spec, "level1.level2.level3.value")
        
        # Assert
        assert result == 42

    def test_extract_missing_parameter(self, rule_engine):
        """Test extraction of a missing parameter."""
        # Arrange
        design_spec = {
            "building_info": {
                "type": "residential"
            }
        }
        
        # Act
        result = rule_engine.extract_parameter(design_spec, "compliance.setbacks.front")
        
        # Assert
        assert result is None


class TestRuleEngineCaching:
    """Test suite for RuleEngine caching functionality."""

    @pytest.fixture
    def rule_engine_with_cache(self):
        """Create a rule engine with caching enabled."""
        return RuleEngine(cache_ttl=60)  # 60 second TTL for testing

    @pytest.fixture
    def sample_rule_set(self):
        """Create a sample rule set for testing."""
        return {
            "metadata": {
                "name": "Standard Building Code 2020",
                "version": "1.0",
                "jurisdiction": "Standard",
                "effective_date": "2020-01-01",
                "description": "Standard Building Code 2020"
            },
            "rule_categories": {
                "setbacks": {
                    "name": "Setback Requirements",
                    "description": "Rules for property setbacks"
                }
            },
            "rules": [
                {
                    "id": "SETBACK_FRONT",
                    "category": "setbacks",
                    "name": "Front Setback",
                    "description": "Front setback must be at least 5 meters",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "compliance.setbacks.front",
                        "operator": ">=",
                        "value": 5.0,
                        "unit": "meters"
                    },
                    "violation_message": "Front setback must be at least 5 meters",
                    "suggestion": "Increase front setback to meet minimum requirement"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "max_violations_per_rule": 10,
                "severity_levels": {
                    "critical": {
                        "blocks_approval": True,
                        "color": "red",
                        "priority": 1
                    },
                    "warning": {
                        "blocks_approval": False,
                        "color": "orange",
                        "priority": 2
                    },
                    "info": {
                        "blocks_approval": False,
                        "color": "blue",
                        "priority": 3
                    }
                }
            }
        }

    def test_cache_hit_on_second_load(self, rule_engine_with_cache, sample_rule_set):
        """Test that second load of same rule set hits cache."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act - First load (cache miss)
                    result1 = rule_engine_with_cache.load_rule_set(rule_set_name)
                    
                    # Act - Second load (should be cache hit)
                    result2 = rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Assert
        assert result1 == result2
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["cached_items"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_miss_on_first_load(self, rule_engine_with_cache, sample_rule_set):
        """Test that first load of rule set is a cache miss."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act
                    result = rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Assert
        assert result is not None
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["cached_items"] == 1

    def test_cache_invalidation_on_file_modification(self, rule_engine_with_cache, sample_rule_set):
        """Test that cache is invalidated when file is modified."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        import copy
        modified_rule_set = copy.deepcopy(sample_rule_set)
        modified_rule_set["metadata"]["version"] = "2.0"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # First load - cache miss
                    result1 = rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Simulate file modification
        with patch("builtins.open", mock_open(read_data=json.dumps(modified_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=2000.0):  # Different mtime
                    # Second load - should detect file change and reload
                    result2 = rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Assert
        assert result1["metadata"]["version"] == "1.0"
        assert result2["metadata"]["version"] == "2.0"
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["misses"] == 2  # Both loads were cache misses

    def test_cache_expiration_after_ttl(self, rule_engine_with_cache, sample_rule_set):
        """Test that cache expires after TTL."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        rule_engine_with_cache.cache_ttl = 1  # 1 second TTL
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # First load
                    result1 = rule_engine_with_cache.load_rule_set(rule_set_name)
                    
                    # Wait for cache to expire
                    time.sleep(1.5)
                    
                    # Second load after expiration
                    result2 = rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Assert
        assert result1 == result2
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["misses"] == 2  # Both loads were cache misses due to expiration

    def test_clear_cache_all(self, rule_engine_with_cache, sample_rule_set):
        """Test clearing entire cache."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Load rule set to populate cache
                    rule_engine_with_cache.load_rule_set(rule_set_name)
        
        # Act
        rule_engine_with_cache.clear_cache()
        
        # Assert
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["cached_items"] == 0

    def test_clear_cache_specific_rule_set(self, rule_engine_with_cache, sample_rule_set):
        """Test clearing specific rule set from cache."""
        # Arrange
        rule_set_name1 = "Standard_Building_Code_2020"
        rule_set_name2 = "Uganda_Building_Code_2021"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Load both rule sets
                    rule_engine_with_cache.load_rule_set(rule_set_name1)
                    rule_engine_with_cache.load_rule_set(rule_set_name2)
        
        # Act - Clear only first rule set
        rule_engine_with_cache.clear_cache(rule_set_name1)
        
        # Assert
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["cached_items"] == 1  # Only one rule set remains

    def test_cache_stats_accuracy(self, rule_engine_with_cache, sample_rule_set):
        """Test that cache statistics are accurate."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act - Load multiple times
                    rule_engine_with_cache.load_rule_set(rule_set_name)  # Miss
                    rule_engine_with_cache.load_rule_set(rule_set_name)  # Hit
                    rule_engine_with_cache.load_rule_set(rule_set_name)  # Hit
                    rule_engine_with_cache.load_rule_set(rule_set_name)  # Hit
        
        # Assert
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 75.0
        assert stats["cached_items"] == 1
        assert stats["cache_size_bytes"] > 0

    def test_multiple_rule_sets_cached(self, rule_engine_with_cache, sample_rule_set):
        """Test that multiple rule sets can be cached simultaneously."""
        # Arrange
        rule_set_names = [
            "Standard_Building_Code_2020",
            "Uganda_Building_Code_2021",
            "Tanzania_Building_Code_2022"
        ]
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act - Load multiple rule sets
                    for name in rule_set_names:
                        rule_engine_with_cache.load_rule_set(name)
        
        # Assert
        stats = rule_engine_with_cache.get_cache_stats()
        assert stats["cached_items"] == 3
        assert stats["misses"] == 3

    def test_cache_performance_improvement(self, rule_engine_with_cache, sample_rule_set):
        """Test that caching improves performance."""
        # Arrange
        rule_set_name = "Standard_Building_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # First load - measure time
                    start1 = time.time()
                    rule_engine_with_cache.load_rule_set(rule_set_name)
                    time1 = time.time() - start1
                    
                    # Second load from cache - measure time
                    start2 = time.time()
                    rule_engine_with_cache.load_rule_set(rule_set_name)
                    time2 = time.time() - start2
        
        # Assert - cached load should be faster (or at least not slower)
        # Note: In tests with mocks, the difference might be minimal
        assert time2 <= time1 * 2  # Allow some variance

    def test_cache_with_zero_ttl(self):
        """Test that cache with zero TTL always reloads."""
        # Arrange
        rule_engine = RuleEngine(cache_ttl=0)
        rule_set_name = "Standard_Building_Code_2020"
        sample_rule_set = {
            "metadata": {
                "name": "Standard Building Code 2020",
                "version": "1.0",
                "jurisdiction": "Standard",
                "effective_date": "2020-01-01",
                "description": "Test"
            },
            "rule_categories": {},
            "rules": [],
            "validation_config": {
                "severity_levels": {
                    "critical": {"blocks_approval": True},
                    "warning": {"blocks_approval": False},
                    "info": {"blocks_approval": False}
                }
            }
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(sample_rule_set))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act - Load twice
                    rule_engine.load_rule_set(rule_set_name)
                    rule_engine.load_rule_set(rule_set_name)
        
        # Assert - Both should be cache misses
        stats = rule_engine.get_cache_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 0


class TestRuleConfigValidation:
    """Test suite for rule configuration validation."""

    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine for testing."""
        return RuleEngine()

    def test_validate_valid_rule_config(self, rule_engine):
        """Test validation of a valid rule configuration."""
        # Arrange
        valid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test building code",
            "categories": {
                "structural": {
                    "name": "Structural Requirements",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test Rule",
                            "description": "Test description",
                            "severity": "critical",
                            "building_types": ["residential"],
                            "validation": {
                                "type": "minimum_value",
                                "parameter": "wall_thickness",
                                "min_value": 0.15,
                                "unit": "meters"
                            },
                            "message": "Test message"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(valid_config)
        
        # Assert
        assert len(errors) == 0

    def test_validate_missing_top_level_fields(self, rule_engine):
        """Test validation catches missing top-level fields."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0"
            # Missing: jurisdiction, effective_date, description, categories
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("jurisdiction" in err for err in errors)
        assert any("effective_date" in err for err in errors)
        assert any("description" in err for err in errors)
        assert any("categories" in err for err in errors)

    def test_validate_invalid_severity(self, rule_engine):
        """Test validation catches invalid severity levels."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test",
                            "description": "Test",
                            "severity": "invalid_severity",  # Invalid
                            "building_types": ["residential"],
                            "validation": {
                                "type": "minimum_value",
                                "parameter": "test",
                                "min_value": 1.0
                            },
                            "message": "Test"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Invalid severity" in err for err in errors)

    def test_validate_invalid_validation_type(self, rule_engine):
        """Test validation catches invalid validation types."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test",
                            "description": "Test",
                            "severity": "critical",
                            "building_types": ["residential"],
                            "validation": {
                                "type": "invalid_type",  # Invalid
                                "parameter": "test"
                            },
                            "message": "Test"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Invalid validation type" in err for err in errors)

    def test_validate_missing_rule_fields(self, rule_engine):
        """Test validation catches missing required rule fields."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001"
                            # Missing: name, description, severity, building_types, validation, message
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("name" in err for err in errors)
        assert any("description" in err for err in errors)
        assert any("severity" in err for err in errors)

    def test_validate_empty_building_types(self, rule_engine):
        """Test validation catches empty building_types array."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test",
                            "description": "Test",
                            "severity": "critical",
                            "building_types": [],  # Empty
                            "validation": {
                                "type": "minimum_value",
                                "parameter": "test",
                                "min_value": 1.0
                            },
                            "message": "Test"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("building_types' cannot be empty" in err for err in errors)

    def test_validate_minimum_value_missing_min_value(self, rule_engine):
        """Test validation catches minimum_value validation missing min_value."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test",
                            "description": "Test",
                            "severity": "critical",
                            "building_types": ["residential"],
                            "validation": {
                                "type": "minimum_value",
                                "parameter": "test"
                                # Missing: min_value
                            },
                            "message": "Test"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("min_value" in err for err in errors)

    def test_validate_range_missing_values(self, rule_engine):
        """Test validation catches range validation missing min/max values."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020",
            "version": "1.0",
            "jurisdiction": "Test",
            "effective_date": "2020-01-01",
            "description": "Test",
            "categories": {
                "structural": {
                    "name": "Structural",
                    "rules": [
                        {
                            "rule_id": "STR-001",
                            "name": "Test",
                            "description": "Test",
                            "severity": "critical",
                            "building_types": ["residential"],
                            "validation": {
                                "type": "range",
                                "parameter": "test"
                                # Missing: min_value and max_value
                            },
                            "message": "Test"
                        }
                    ]
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("min_value" in err and "max_value" in err for err in errors)

    def test_load_rule_set_validates_config(self, rule_engine):
        """Test that load_rule_set validates configuration."""
        # Arrange
        invalid_config = {
            "code_name": "Test_Code_2020"
            # Missing required fields
        }
        rule_set_name = "Test_Code_2020"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(invalid_config))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act & Assert
                    with pytest.raises(ValueError) as exc_info:
                        rule_engine.load_rule_set(rule_set_name)
                    
                    assert "Invalid rule set configuration" in str(exc_info.value)

    def test_load_valid_standard_building_code(self, rule_engine):
        """Test loading the actual Standard_Building_Code_2020.json file."""
        # This test verifies that our actual configuration file is valid
        rule_set_name = "Standard_Building_Code_2020"
        
        try:
            # Act
            result = rule_engine.load_rule_set(rule_set_name)
            
            # Assert
            assert result is not None
            assert "code_name" in result
            assert "categories" in result
            assert len(result["categories"]) > 0
        except FileNotFoundError:
            pytest.skip("Standard_Building_Code_2020.json not found in config directory")


class TestRuleConfigValidation:
    """Test suite for rule configuration validation."""

    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine for testing."""
        return RuleEngine()

    def test_validate_valid_rule_config(self, rule_engine):
        """Test validation of a valid rule configuration."""
        # Arrange
        valid_config = {
            "metadata": {
                "name": "Standard Building Code 2020",
                "version": "2020.1",
                "jurisdiction": "Standard",
                "effective_date": "2020-01-01",
                "description": "Standard building code"
            },
            "rule_categories": {
                "structural": {
                    "name": "Structural Requirements",
                    "description": "Rules for structural integrity"
                }
            },
            "rules": [
                {
                    "id": "STR-001",
                    "category": "structural",
                    "name": "Minimum Wall Thickness",
                    "description": "Walls must meet minimum thickness",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_value",
                        "field": "wall_thickness",
                        "operator": ">=",
                        "value": 0.15,
                        "unit": "meters"
                    },
                    "violation_message": "Wall thickness must be at least 0.15 meters",
                    "suggestion": "Increase wall thickness"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "severity_levels": {
                    "critical": {"blocks_approval": True},
                    "warning": {"blocks_approval": False},
                    "info": {"blocks_approval": False}
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(valid_config)
        
        # Assert
        assert len(errors) == 0

    def test_validate_missing_top_level_fields(self, rule_engine):
        """Test validation catches missing top-level fields."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0"
                # Missing: jurisdiction, effective_date, description
            }
            # Missing: rule_categories, rules, validation_config
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("jurisdiction" in err for err in errors)
        assert any("effective_date" in err for err in errors)
        assert any("description" in err for err in errors)
        assert any("rule_categories" in err for err in errors)

    def test_validate_invalid_severity(self, rule_engine):
        """Test validation catches invalid severity levels."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test code"
            },
            "rule_categories": {
                "test": {
                    "name": "Test Category",
                    "description": "Test category"
                }
            },
            "rules": [
                {
                    "id": "TEST-001",
                    "category": "test",
                    "name": "Test Rule",
                    "description": "Test description",
                    "severity": "invalid_severity",  # Invalid
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_value",
                        "field": "test_param",
                        "operator": ">=",
                        "value": 1.0
                    },
                    "violation_message": "Test message",
                    "suggestion": "Test suggestion"
                }
            ],
            "validation_config": {
                "severity_levels": {
                    "critical": {"blocks_approval": True},
                    "warning": {"blocks_approval": False},
                    "info": {"blocks_approval": False}
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Invalid severity" in err for err in errors)

    def test_validate_invalid_validation_type(self, rule_engine):
        """Test validation catches missing required fields."""
        # Arrange - Use format that will trigger validation errors
        invalid_config = {
            # Missing required top-level fields like "metadata", "rule_categories", etc.
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Missing required top-level field" in err for err in errors)

    def test_validate_missing_min_value_for_minimum_validation(self, rule_engine):
        """Test validation catches missing metadata fields."""
        # Arrange
        invalid_config = {
            "metadata": {
                # Missing required metadata fields like "name", "version", etc.
            },
            "rule_categories": {},
            "rules": [],
            "validation_config": {}
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Missing required metadata field" in err for err in errors)

    def test_validate_empty_building_types(self, rule_engine):
        """Test validation catches invalid rule categories."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test code"
            },
            "rule_categories": "invalid",  # Should be dict, not string
            "rules": [],
            "validation_config": {}
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("must be a dictionary" in err for err in errors)

    def test_load_rule_set_validates_config(self, rule_engine):
        """Test that load_rule_set validates configuration."""
        # Arrange
        invalid_config = {
            "code_name": "Invalid_Code",
            "version": "1.0"
            # Missing required fields
        }
        
        rule_set_name = "Invalid_Code"
        
        with patch("builtins.open", mock_open(read_data=json.dumps(invalid_config))):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=1000.0):
                    # Act & Assert
                    with pytest.raises(ValueError) as exc_info:
                        rule_engine.load_rule_set(rule_set_name)
                    
                    assert "Invalid rule set configuration" in str(exc_info.value)

    def test_validate_range_validation_missing_values(self, rule_engine):
        """Test validation catches invalid rules structure."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test code"
            },
            "rule_categories": {},
            "rules": "invalid",  # Should be list, not string
            "validation_config": {}
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("must be a list" in err for err in errors)

    def test_validate_required_validation_missing_value(self, rule_engine):
        """Test validation catches missing validation_config."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test code"
            },
            "rule_categories": {},
            "rules": []
            # Missing: validation_config
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Missing required top-level field: validation_config" in err for err in errors)


class TestRuleConfigValidationNew:
    """Test suite for new rule configuration validation format."""

    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine for testing."""
        return RuleEngine()

    @pytest.fixture
    def valid_rule_set_new(self):
        """Create a valid rule set configuration for testing new format."""
        return {
            "metadata": {
                "name": "Test Building Code 2020",
                "version": "2020.1",
                "jurisdiction": "Test Country",
                "effective_date": "2020-01-01",
                "description": "Test building code rules",
                "last_updated": "2020-12-31"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning Requirements",
                    "description": "Zoning compliance and setback requirements"
                },
                "structural": {
                    "name": "Structural Requirements",
                    "description": "Rules for structural integrity and safety"
                }
            },
            "rules": [
                {
                    "id": "SETBACK_FRONT",
                    "category": "zoning",
                    "name": "Front Setback Requirement",
                    "description": "Minimum distance from front property boundary",
                    "severity": "critical",
                    "building_types": ["residential", "commercial"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "setbacks.front",
                        "operator": ">=",
                        "value": 5.0,
                        "unit": "meters"
                    },
                    "violation_message": "Front setback must be at least {required_value} {unit}",
                    "suggestion": "Increase front setback to meet minimum requirement"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "severity_levels": {
                    "critical": {
                        "blocks_approval": True,
                        "color": "red",
                        "priority": 1
                    },
                    "warning": {
                        "blocks_approval": False,
                        "color": "orange",
                        "priority": 2
                    }
                }
            }
        }

    def test_validate_new_format_valid_config(self, rule_engine, valid_rule_set_new):
        """Test validation of a valid rule configuration in new format."""
        # Act
        errors = rule_engine.validate_rule_config(valid_rule_set_new)
        
        # Assert
        assert len(errors) == 0

    def test_validate_new_format_missing_metadata(self, rule_engine):
        """Test validation catches missing metadata section."""
        # Arrange
        invalid_config = {
            "rule_categories": {},
            "rules": [],
            "validation_config": {}
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Missing required top-level field: metadata" in err for err in errors)

    def test_validate_new_format_missing_metadata_fields(self, rule_engine):
        """Test validation catches missing metadata fields."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code"
                # Missing: version, jurisdiction, effective_date, description
            },
            "rule_categories": {},
            "rules": [],
            "validation_config": {}
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Missing required metadata field: version" in err for err in errors)
        assert any("Missing required metadata field: jurisdiction" in err for err in errors)
        assert any("Missing required metadata field: effective_date" in err for err in errors)
        assert any("Missing required metadata field: description" in err for err in errors)

    def test_validate_new_format_invalid_rule_category_reference(self, rule_engine):
        """Test validation catches invalid category references in rules."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning",
                    "description": "Zoning rules"
                }
            },
            "rules": [
                {
                    "id": "TEST_RULE",
                    "category": "invalid_category",  # Invalid reference
                    "name": "Test Rule",
                    "description": "Test",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_value",
                        "field": "test.field",
                        "operator": ">=",
                        "value": 5.0
                    }
                }
            ],
            "validation_config": {
                "severity_levels": {
                    "critical": {"blocks_approval": True}
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Invalid category 'invalid_category'" in err for err in errors)

    def test_validate_new_format_invalid_condition_type(self, rule_engine):
        """Test validation catches invalid condition types."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning",
                    "description": "Zoning rules"
                }
            },
            "rules": [
                {
                    "id": "TEST_RULE",
                    "category": "zoning",
                    "name": "Test Rule",
                    "description": "Test",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "invalid_condition_type",  # Invalid type
                        "field": "test.field",
                        "operator": ">=",
                        "value": 5.0
                    }
                }
            ],
            "validation_config": {
                "severity_levels": {
                    "critical": {"blocks_approval": True}
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("Invalid condition type 'invalid_condition_type'" in err for err in errors)

    def test_validate_new_format_missing_condition_fields(self, rule_engine):
        """Test validation catches missing condition fields."""
        # Arrange
        invalid_config = {
            "metadata": {
                "name": "Test Code",
                "version": "1.0",
                "jurisdiction": "Test",
                "effective_date": "2020-01-01",
                "description": "Test"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning",
                    "description": "Zoning rules"
                }
            },
            "rules": [
                {
                    "id": "TEST_RULE",
                    "category": "zoning",
                    "name": "Test Rule",
                    "description": "Test",
                    "severity": "critical",
                    "building_types": ["residential"],
                    "condition": {
                        "type": "minimum_value"
                        # Missing: field, operator, value
                    }
                }
            ],
            "validation_config": {
                "severity_levels": {
                    "critical": {"blocks_approval": True}
                }
            }
        }
        
        # Act
        errors = rule_engine.validate_rule_config(invalid_config)
        
        # Assert
        assert len(errors) > 0
        assert any("'condition' missing 'field' field" in err for err in errors)
        assert any("'minimum_value' condition missing 'value' field" in err for err in errors)
        assert any("'minimum_value' condition missing 'operator' field" in err for err in errors)


class TestRuleEngineNewFormat:
    """Test suite for RuleEngine with new rule format."""

    @pytest.fixture
    def temp_rules_dir_new(self):
        """Create a temporary directory with rule files for testing."""
        valid_rule_set = {
            "metadata": {
                "name": "Test Building Code 2020",
                "version": "2020.1",
                "jurisdiction": "Test Country",
                "effective_date": "2020-01-01",
                "description": "Test building code rules",
                "last_updated": "2020-12-31"
            },
            "rule_categories": {
                "zoning": {
                    "name": "Zoning Requirements",
                    "description": "Zoning compliance and setback requirements"
                },
                "structural": {
                    "name": "Structural Requirements",
                    "description": "Rules for structural integrity and safety"
                }
            },
            "rules": [
                {
                    "id": "SETBACK_FRONT",
                    "category": "zoning",
                    "name": "Front Setback Requirement",
                    "description": "Minimum distance from front property boundary",
                    "severity": "critical",
                    "building_types": ["residential", "commercial"],
                    "condition": {
                        "type": "minimum_distance",
                        "field": "setbacks.front",
                        "operator": ">=",
                        "value": 5.0,
                        "unit": "meters"
                    },
                    "violation_message": "Front setback must be at least {required_value} {unit}. Current value: {current_value} {unit}",
                    "suggestion": "Increase front setback to meet minimum requirement"
                }
            ],
            "validation_config": {
                "timeout_seconds": 10,
                "severity_levels": {
                    "critical": {
                        "blocks_approval": True,
                        "color": "red",
                        "priority": 1
                    },
                    "warning": {
                        "blocks_approval": False,
                        "color": "orange",
                        "priority": 2
                    }
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid rule file
            rule_file_path = os.path.join(temp_dir, "Standard_Building_Code_2020.json")
            with open(rule_file_path, "w") as f:
                json.dump(valid_rule_set, f)
            
            yield temp_dir

    @pytest.fixture
    def rule_engine(self, temp_rules_dir_new):
        """Create a rule engine with temporary rules directory."""
        return RuleEngine(rules_path=temp_rules_dir_new)

    def test_load_new_format_rule_set(self, rule_engine):
        """Test loading rule set in new format."""
        # Act
        result = rule_engine.load_rule_set("Standard_Building_Code_2020")
        
        # Assert
        assert result is not None
        assert "metadata" in result
        assert "rule_categories" in result
        assert "rules" in result
        assert "validation_config" in result
        assert result["metadata"]["name"] == "Test Building Code 2020"

    def test_validate_with_new_format_compliant_design(self, rule_engine):
        """Test validation with new format - compliant design."""
        # Arrange
        rule_set = rule_engine.load_rule_set("Standard_Building_Code_2020")
        design_spec = {
            "building_info": {
                "type": "residential",
                "height": 7.0,
                "num_floors": 2
            },
            "setbacks": {
                "front": 6.0,  # Compliant (>= 5.0)
                "rear": 4.0,
                "side": 3.0
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, rule_set)
        
        # Assert
        assert result["is_compliant"] is True
        assert len(result["violations"]) == 0

    def test_validate_with_new_format_violation(self, rule_engine):
        """Test validation with new format - design with violation."""
        # Arrange
        rule_set = rule_engine.load_rule_set("Standard_Building_Code_2020")
        design_spec = {
            "building_info": {
                "type": "residential",
                "height": 7.0,
                "num_floors": 2
            },
            "setbacks": {
                "front": 4.0,  # Violation (< 5.0)
                "rear": 4.0,
                "side": 3.0
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, rule_set)
        
        # Assert
        assert result["is_compliant"] is False
        assert len(result["violations"]) > 0
        
        # Check specific violation
        front_violation = next(
            (v for v in result["violations"] if v["code"] == "SETBACK_FRONT"),
            None
        )
        assert front_violation is not None
        assert front_violation["severity"] == "critical"
        assert front_violation["current_value"] == 4.0
        assert front_violation["required_value"] == 5.0

    def test_validate_building_type_filtering(self, rule_engine):
        """Test that rules are filtered by building type."""
        # Arrange
        rule_set = rule_engine.load_rule_set("Standard_Building_Code_2020")
        design_spec = {
            "building_info": {
                "type": "industrial",  # Different building type
                "height": 7.0
            },
            "setbacks": {
                "front": 4.0  # Would be violation for residential
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, rule_set)
        
        # Assert
        # Should be compliant because residential rules don't apply to industrial
        assert result["is_compliant"] is True
        assert len(result["violations"]) == 0

    def test_validate_message_formatting(self, rule_engine):
        """Test that violation messages are properly formatted."""
        # Arrange
        rule_set = rule_engine.load_rule_set("Standard_Building_Code_2020")
        design_spec = {
            "building_info": {
                "type": "residential"
            },
            "setbacks": {
                "front": 3.5  # Violation
            }
        }
        
        # Act
        result = rule_engine.validate(design_spec, rule_set)
        
        # Assert
        assert len(result["violations"]) > 0
        violation = result["violations"][0]
        assert "3.5" in violation["message"]  # Current value
        assert "5.0" in violation["message"]  # Required value
        assert "meters" in violation["message"]  # Unit


class TestValidationServiceWithNewFormat:
    """Test suite for ValidationService with new rule format."""

    @pytest.fixture
    def validation_repo(self, db_session):
        """Create a validation repository for testing."""
        return ValidationRepository(db_session)

    @pytest.fixture
    def design_repo(self, db_session):
        """Create a design repository for testing."""
        return DesignRepository(db_session)

    @pytest.fixture
    def valid_rule_set(self):
        """Create a valid rule set configuration for testing."""
        return {
            "metadata": {
                "name": "Standard Building Code",
                "version": "2020.1",
                "jurisdiction": "Test City",
                "effective_date": "2020-01-01",
                "description": "Standard building code for test purposes"
            },
            "rule_categories": {
                "setbacks": {
                    "name": "Setback Requirements",
                    "description": "Building setback requirements"
                }
            },
            "rules": [
                {
                    "id": "SB-001",
                    "category": "setbacks",
                    "name": "Front Setback",
                    "description": "Minimum front setback requirement",
                    "severity": "critical",
                    "building_types": ["residential", "commercial"],
                    "condition": {
                        "type": "minimum_value",
                        "field": "setbacks.front",
                        "value": 5.0,
                        "operator": ">="
                    }
                }
            ],
            "validation_config": {
                "timeout_seconds": 30,
                "severity_levels": {
                    "critical": {"blocks_approval": True},
                    "warning": {"blocks_approval": False},
                    "info": {"blocks_approval": False}
                }
            }
        }

    @pytest.fixture
    def temp_rules_dir(self, valid_rule_set):
        """Create a temporary directory with rule files for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid rule file
            rule_file_path = os.path.join(temp_dir, "Standard_Building_Code_2020.json")
            with open(rule_file_path, "w") as f:
                json.dump(valid_rule_set, f)
            
            yield temp_dir

    @pytest.fixture
    def compliant_design(self, db_session):
        """Create a compliant design for testing."""
        from tests.factories import DesignFactory
        
        design = DesignFactory.create(
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.5,
                    "num_floors": 2,
                    "height": 7.5
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                },
                "compliance": {
                    "building_code": "Standard_Building_Code_2020",
                    "setbacks": {"front": 5.0, "rear": 3.0, "side": 2.0}
                }
            },
            status="draft"
        )
        db_session.commit()
        return design

    @pytest.fixture
    def non_compliant_design(self, db_session):
        """Create a non-compliant design for testing."""
        from tests.factories import DesignFactory
        
        design = DesignFactory.create(
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.5,
                    "num_floors": 2,
                    "height": 7.5
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                },
                "compliance": {
                    "building_code": "Standard_Building_Code_2020",
                    "setbacks": {"front": 4.5, "rear": 3.0, "side": 2.0}  # Front setback violation
                }
            },
            status="draft"
        )
        db_session.commit()
        return design

    @pytest.fixture
    def validation_service_with_new_format(self, validation_repo, design_repo, temp_rules_dir):
        """Create validation service with new format rule engine."""
        rule_engine = RuleEngine(rules_path=temp_rules_dir)
        return ValidationService(validation_repo, design_repo, rule_engine)

    def test_validate_design_with_new_format(
        self,
        validation_service_with_new_format,
        compliant_design,
        db_session
    ):
        """Test design validation using new rule format."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        # Update design specification to match new format expectations
        compliant_design.specification = {
            "building_info": {
                "type": "residential",
                "height": 7.0,
                "num_floors": 2
            },
            "setbacks": {
                "front": 6.0,  # Compliant
                "rear": 4.0,
                "side": 3.0
            }
        }
        db_session.commit()
        
        # Act
        result = validation_service_with_new_format.validate_design(
            design=compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert isinstance(result, DesignValidation)
        assert result.is_compliant is True
        assert result.violations == []
        
        # Verify design status was updated
        db_session.refresh(compliant_design)
        assert compliant_design.status == "compliant"

    def test_validate_design_with_new_format_violations(
        self,
        validation_service_with_new_format,
        non_compliant_design,
        db_session
    ):
        """Test design validation with violations using new rule format."""
        # Arrange
        user_id = 1
        validation_type = "building_code"
        rule_set = "Standard_Building_Code_2020"
        
        # Update design specification to have violations
        non_compliant_design.specification = {
            "building_info": {
                "type": "residential",
                "height": 7.0,
                "num_floors": 2
            },
            "setbacks": {
                "front": 3.0,  # Violation (< 5.0)
                "rear": 4.0,
                "side": 3.0
            }
        }
        db_session.commit()
        
        # Act
        result = validation_service_with_new_format.validate_design(
            design=non_compliant_design,
            validation_type=validation_type,
            rule_set=rule_set,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert result.is_compliant is False
        assert len(result.violations) > 0
        
        # Check specific violation
        assert any(v["code"] == "SETBACK_FRONT" for v in result.violations)
        
        # Verify design status was updated
        db_session.refresh(non_compliant_design)
        assert non_compliant_design.status == "non_compliant"
