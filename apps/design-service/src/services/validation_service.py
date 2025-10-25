"""
ValidationService for design validation against building codes.

This service provides:
- Design validation against building code rule sets
- Rule engine for checking compliance
- Violation and warning collection
- Design status updates based on validation results
- In-memory caching of building code rules for performance
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from ..models.design import Design
from ..models.design_validation import DesignValidation
from ..repositories.validation_repository import ValidationRepository
from ..repositories.design_repository import DesignRepository


class RuleEngine:
    """
    Rule engine for validating designs against building code rules.
    
    Loads rule sets from configuration files and validates design specifications
    against defined rules. Implements in-memory caching for performance optimization.
    
    Caching Strategy:
    - Rule sets are cached in memory with a TTL (time-to-live) of 1 hour
    - Cache entries include the rule set data and file modification time
    - Cache is automatically invalidated if the source file is modified
    - Cache can be manually cleared using clear_cache() method
    - Cache statistics (hits/misses) are tracked for monitoring
    """

    # Valid validation types
    VALID_VALIDATION_TYPES = {
        "minimum_value",
        "maximum_value",
        "minimum_count",
        "required",
        "minimum_percentage",
        "range"
    }

    # Valid severity levels
    VALID_SEVERITIES = {"critical", "warning", "info"}

    def __init__(
        self,
        rules_path: Optional[str] = None,
        cache_ttl: int = 3600  # 1 hour default TTL
    ):
        """
        Initialize the rule engine with caching support.

        Args:
            rules_path: Path to building code rules directory
                       (default: ./config/building_codes)
            cache_ttl: Time-to-live for cached rule sets in seconds (default: 3600)
        """
        if rules_path is None:
            # Default to config/building_codes relative to project root
            rules_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "config",
                "building_codes"
            )
        self.rules_path = rules_path
        self.cache_ttl = cache_ttl
        
        # Cache structure: {rule_set_name: (rule_set_data, timestamp, file_mtime)}
        self._cache: Dict[str, Tuple[Dict[str, Any], float, float]] = {}
        
        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

    def validate_rule_config(self, rule_set: Dict[str, Any]) -> List[str]:
        """
        Validate the structure and content of a building code configuration.

        Args:
            rule_set: Rule set configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate top-level required fields
        required_top_level = ["metadata", "rule_categories", "rules", "validation_config"]
        for field in required_top_level:
            if field not in rule_set:
                errors.append(f"Missing required top-level field: {field}")

        # Validate metadata structure
        if "metadata" in rule_set:
            metadata = rule_set["metadata"]
            if not isinstance(metadata, dict):
                errors.append("'metadata' must be a dictionary")
            else:
                required_metadata = ["name", "version", "jurisdiction", "effective_date", "description"]
                for field in required_metadata:
                    if field not in metadata:
                        errors.append(f"Missing required metadata field: {field}")

        # Validate rule_categories structure
        if "rule_categories" in rule_set:
            categories = rule_set["rule_categories"]
            if not isinstance(categories, dict):
                errors.append("'rule_categories' must be a dictionary")
            else:
                for category_id, category in categories.items():
                    if not isinstance(category, dict):
                        errors.append(f"Category '{category_id}' must be a dictionary")
                        continue
                    
                    required_category_fields = ["name", "description"]
                    for field in required_category_fields:
                        if field not in category:
                            errors.append(f"Category '{category_id}' missing required field: {field}")

        # Validate rules structure
        if "rules" in rule_set:
            rules = rule_set["rules"]
            if not isinstance(rules, list):
                errors.append("'rules' must be a list")
            else:
                for idx, rule in enumerate(rules):
                    rule_prefix = f"Rule {idx}"
                    
                    if not isinstance(rule, dict):
                        errors.append(f"{rule_prefix}: Rule must be a dictionary")
                        continue

                    # Validate required rule fields
                    required_rule_fields = ["id", "category", "name", "description", "severity", "building_types", "condition"]
                    for field in required_rule_fields:
                        if field not in rule:
                            errors.append(f"{rule_prefix}: Missing required field '{field}'")

                    # Validate severity
                    if "severity" in rule and rule["severity"] not in self.VALID_SEVERITIES:
                        errors.append(
                            f"{rule_prefix}: Invalid severity '{rule['severity']}'. "
                            f"Must be one of: {', '.join(self.VALID_SEVERITIES)}"
                        )

                    # Validate building_types
                    if "building_types" in rule:
                        if not isinstance(rule["building_types"], list):
                            errors.append(f"{rule_prefix}: 'building_types' must be a list")
                        elif len(rule["building_types"]) == 0:
                            errors.append(f"{rule_prefix}: 'building_types' cannot be empty")

                    # Validate category reference
                    if "category" in rule and "rule_categories" in rule_set:
                        category_id = rule["category"]
                        if category_id not in rule_set["rule_categories"]:
                            errors.append(f"{rule_prefix}: Invalid category '{category_id}'. Must be defined in rule_categories")

                    # Validate condition structure
                    if "condition" in rule:
                        condition = rule["condition"]
                        if not isinstance(condition, dict):
                            errors.append(f"{rule_prefix}: 'condition' must be a dictionary")
                            continue

                        if "type" not in condition:
                            errors.append(f"{rule_prefix}: 'condition' missing 'type' field")
                        else:
                            condition_type = condition["type"]
                            valid_condition_types = {
                                "minimum_value", "maximum_value", "minimum_distance", "minimum_area",
                                "minimum_count", "minimum_percentage", "required_field"
                            }
                            if condition_type not in valid_condition_types:
                                errors.append(
                                    f"{rule_prefix}: Invalid condition type '{condition_type}'. "
                                    f"Must be one of: {', '.join(valid_condition_types)}"
                                )

                        if "field" not in condition:
                            errors.append(f"{rule_prefix}: 'condition' missing 'field' field")

                        # Type-specific validation
                        condition_type = condition.get("type")
                        if condition_type in ["minimum_value", "maximum_value", "minimum_distance", "minimum_area", "minimum_count", "minimum_percentage"]:
                            if "value" not in condition:
                                errors.append(f"{rule_prefix}: '{condition_type}' condition missing 'value' field")
                            if "operator" not in condition:
                                errors.append(f"{rule_prefix}: '{condition_type}' condition missing 'operator' field")
                        elif condition_type == "required_field":
                            # For required_field, value or allowed_values should be present
                            if "value" not in condition and "allowed_values" not in condition:
                                errors.append(f"{rule_prefix}: 'required_field' condition missing 'value' or 'allowed_values' field")

        # Validate validation_config structure
        if "validation_config" in rule_set:
            config = rule_set["validation_config"]
            if not isinstance(config, dict):
                errors.append("'validation_config' must be a dictionary")
            else:
                if "severity_levels" in config:
                    severity_levels = config["severity_levels"]
                    if not isinstance(severity_levels, dict):
                        errors.append("'validation_config.severity_levels' must be a dictionary")
                    else:
                        for severity, level_config in severity_levels.items():
                            if severity not in self.VALID_SEVERITIES:
                                errors.append(f"Invalid severity level '{severity}' in validation_config")
                            if not isinstance(level_config, dict):
                                errors.append(f"Severity level config for '{severity}' must be a dictionary")

        return errors

    def load_rule_set(self, rule_set_name: str) -> Dict[str, Any]:
        """
        Load a building code rule set from configuration with caching.
        
        This method implements an in-memory cache with the following features:
        - Cached rule sets are reused for subsequent requests
        - Cache entries expire after the configured TTL
        - Cache is automatically invalidated if the source file is modified
        - Cache statistics are tracked for monitoring

        Args:
            rule_set_name: Name of the rule set (e.g., "Kenya_Building_Code_2020")

        Returns:
            Dictionary containing the rule set configuration

        Raises:
            FileNotFoundError: If rule set file doesn't exist
            ValueError: If rule set format is invalid
        """
        rule_set_path = os.path.join(self.rules_path, f"{rule_set_name}.json")

        if not os.path.exists(rule_set_path):
            raise FileNotFoundError(
                f"Rule set not found: {rule_set_name} at {rule_set_path}"
            )

        # Get file modification time
        file_mtime = os.path.getmtime(rule_set_path)
        current_time = time.time()

        # Check if we have a valid cached entry
        if rule_set_name in self._cache:
            cached_data, cache_time, cached_mtime = self._cache[rule_set_name]
            
            # Check if cache is still valid (not expired and file not modified)
            cache_age = current_time - cache_time
            file_modified = file_mtime != cached_mtime
            
            if cache_age < self.cache_ttl and not file_modified:
                # Cache hit - return cached data
                self._cache_hits += 1
                return cached_data
            else:
                # Cache expired or file modified - remove from cache
                del self._cache[rule_set_name]

        # Cache miss - load from file
        self._cache_misses += 1
        
        try:
            with open(rule_set_path, "r", encoding="utf-8") as f:
                rule_set = json.load(f)
            
            # Validate rule set structure
            validation_errors = self.validate_rule_config(rule_set)
            if validation_errors:
                error_msg = f"Invalid rule set configuration for '{rule_set_name}':\n"
                error_msg += "\n".join(f"  - {err}" for err in validation_errors)
                raise ValueError(error_msg)
            
            # Store in cache with current timestamp and file mtime
            self._cache[rule_set_name] = (rule_set, current_time, file_mtime)
            
            return rule_set
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid rule set format: {e}")

    def clear_cache(self, rule_set_name: Optional[str] = None) -> None:
        """
        Clear the rule set cache.
        
        This method allows manual cache invalidation, useful when:
        - Rule set files are updated externally
        - Memory needs to be freed
        - Testing cache behavior

        Args:
            rule_set_name: Specific rule set to clear, or None to clear all
        """
        if rule_set_name is None:
            # Clear entire cache
            self._cache.clear()
        elif rule_set_name in self._cache:
            # Clear specific rule set
            del self._cache[rule_set_name]

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring and debugging.

        Returns:
            Dictionary containing cache statistics:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate as a percentage
            - cached_items: Number of items currently in cache
            - cache_size: Approximate memory size of cache in bytes
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        # Estimate cache size (rough approximation)
        cache_size = sum(
            len(json.dumps(data))
            for data, _, _ in self._cache.values()
        )
        
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": round(hit_rate, 2),
            "cached_items": len(self._cache),
            "cache_size_bytes": cache_size
        }

    def extract_parameter(
        self,
        design_spec: Dict[str, Any],
        path: str
    ) -> Optional[Any]:
        """
        Extract a parameter from design specification using dot notation path.

        Args:
            design_spec: Design specification dictionary
            path: Dot-notation path (e.g., "compliance.setbacks.front")

        Returns:
            Parameter value if found, None otherwise
        """
        parts = path.split(".")
        current = design_spec

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def validate(
        self,
        design_spec: Dict[str, Any],
        rule_set: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a design specification against a rule set.

        Args:
            design_spec: Design specification to validate
            rule_set: Rule set configuration

        Returns:
            Dictionary with validation results:
            {
                "is_compliant": bool,
                "violations": List[Dict],
                "warnings": List[Dict]
            }
        """
        violations = []
        warnings = []

        rules = rule_set.get("rules", [])
        building_type = design_spec.get("building_info", {}).get("type", "")

        for rule in rules:
            rule_id = rule.get("id")
            severity = rule.get("severity", "critical")
            name = rule.get("name", "")
            description = rule.get("description", "")
            building_types = rule.get("building_types", [])
            condition = rule.get("condition", {})
            violation_message = rule.get("violation_message", description)
            suggestion = rule.get("suggestion", "")

            # Skip rule if it doesn't apply to this building type
            if building_type and building_types and building_type not in building_types:
                continue

            condition_type = condition.get("type")
            field_path = condition.get("field")
            operator = condition.get("operator", ">=")
            required_value = condition.get("value")
            unit = condition.get("unit", "")

            # Extract the parameter value from design spec
            current_value = self.extract_parameter(design_spec, field_path)

            # Handle different condition types
            violation_found = False
            
            if condition_type in ["minimum_value", "minimum_distance", "minimum_area"]:
                if current_value is not None and operator == ">=" and current_value < required_value:
                    violation_found = True
                elif current_value is not None and operator == ">" and current_value <= required_value:
                    violation_found = True

            elif condition_type == "maximum_value":
                if current_value is not None and operator == "<=" and current_value > required_value:
                    violation_found = True
                elif current_value is not None and operator == "<" and current_value >= required_value:
                    violation_found = True

            elif condition_type == "minimum_count":
                # Check if applies_when condition is met
                applies_when = condition.get("applies_when")
                if applies_when:
                    applies_field = applies_when.get("field")
                    applies_operator = applies_when.get("operator", ">")
                    applies_value = applies_when.get("value")
                    applies_current = self.extract_parameter(design_spec, applies_field)
                    
                    # Only apply rule if condition is met
                    if applies_current is None:
                        continue
                    if applies_operator == ">" and applies_current <= applies_value:
                        continue
                    elif applies_operator == ">=" and applies_current < applies_value:
                        continue
                    elif applies_operator == "<" and applies_current >= applies_value:
                        continue
                    elif applies_operator == "<=" and applies_current > applies_value:
                        continue
                    elif applies_operator == "==" and applies_current != applies_value:
                        continue

                if current_value is not None and operator == ">=" and current_value < required_value:
                    violation_found = True

            elif condition_type == "required_field":
                allowed_values = condition.get("allowed_values")
                if current_value is None:
                    violation_found = True
                elif allowed_values and current_value not in allowed_values:
                    violation_found = True
                elif "value" in condition and current_value != condition["value"]:
                    violation_found = True

            elif condition_type == "minimum_percentage":
                # For percentage-based rules, we need to implement JSONPath-like logic
                # This is a simplified implementation
                if current_value is not None and operator == ">=" and current_value < required_value:
                    violation_found = True

            # Create violation/warning if found
            if violation_found:
                # Format violation message with template variables
                formatted_message = violation_message.format(
                    required_value=required_value,
                    current_value=current_value,
                    unit=unit,
                    allowed_values=condition.get("allowed_values", [])
                )

                violation_data = {
                    "code": rule_id,
                    "severity": severity,
                    "rule": name,
                    "message": formatted_message,
                    "current_value": current_value,
                    "required_value": required_value,
                    "location": field_path.split(".")[-1] if field_path else "",
                    "suggestion": suggestion
                }

                if severity == "critical":
                    violations.append(violation_data)
                else:
                    warnings.append(violation_data)

        # Design is compliant if there are no critical violations
        is_compliant = len(violations) == 0

        return {
            "is_compliant": is_compliant,
            "violations": violations,
            "warnings": warnings
        }


class ValidationService:
    """
    Service for validating designs against building codes.
    
    Provides design validation functionality including:
    - Loading and parsing building code rule sets
    - Running validation rules against design specifications
    - Collecting violations and warnings
    - Updating design status based on validation results
    """

    def __init__(
        self,
        validation_repo: ValidationRepository,
        design_repo: DesignRepository,
        rule_engine: Optional[RuleEngine] = None
    ):
        """
        Initialize the validation service.

        Args:
            validation_repo: Repository for validation operations
            design_repo: Repository for design operations
            rule_engine: Rule engine for validation (optional, creates default if None)
        """
        self.validation_repo = validation_repo
        self.design_repo = design_repo
        self.rule_engine = rule_engine if rule_engine else RuleEngine()

    def validate_design(
        self,
        design: Design,
        validation_type: str,
        rule_set: str,
        user_id: int
    ) -> DesignValidation:
        """
        Validate a design against specified building code rules.

        This method:
        1. Loads the rule set configuration
        2. Extracts design parameters from specification
        3. Runs validation rules
        4. Collects violations and warnings
        5. Creates DesignValidation entity
        6. Updates design status based on validation result

        Args:
            design: Design instance to validate
            validation_type: Type of validation (building_code, structural, safety)
            rule_set: Building code rule set name (e.g., "Kenya_Building_Code_2020")
            user_id: ID of user performing validation

        Returns:
            Created DesignValidation instance

        Raises:
            FileNotFoundError: If rule set doesn't exist
            ValueError: If rule set format is invalid
        """
        # Load rule set configuration
        rule_set_config = self.rule_engine.load_rule_set(rule_set)

        # Extract design specification
        design_spec = design.specification

        # Run validation rules
        validation_result = self.rule_engine.validate(design_spec, rule_set_config)

        # Create DesignValidation entity
        validation = self.validation_repo.create_validation(
            design_id=design.id,
            validation_type=validation_type,
            rule_set=rule_set,
            is_compliant=validation_result["is_compliant"],
            violations=validation_result["violations"],
            warnings=validation_result["warnings"],
            validated_by=user_id
        )

        # Update design status based on validation result
        if validation_result["is_compliant"]:
            # Design is compliant (may have warnings but no critical violations)
            new_status = "compliant"
        else:
            # Design has critical violations
            new_status = "non_compliant"

        # Update design status
        self.design_repo.update_design(
            design_id=design.id,
            status=new_status
        )

        return validation
