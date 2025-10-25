# Building Code Configuration

This directory contains building code rule sets used by the Design Service for validating architectural designs against regulatory requirements.

## Rule File Format

Building code rule files are JSON documents that define validation rules for different building types and jurisdictions. Each file follows a standardized structure to ensure consistent validation across different code sets.

### File Structure

```json
{
  "metadata": {
    "name": "Building Code Name",
    "version": "Version Number",
    "jurisdiction": "Geographic Area",
    "effective_date": "YYYY-MM-DD",
    "description": "Description of the code",
    "last_updated": "YYYY-MM-DD"
  },
  "rule_categories": {
    "category_id": {
      "name": "Category Display Name",
      "description": "Category description"
    }
  },
  "rules": [
    // Array of rule objects
  ],
  "validation_config": {
    // Validation configuration
  }
}
```

## Rule Object Structure

Each rule in the `rules` array follows this structure:

### Basic Rule Properties

- **id** (string, required): Unique identifier for the rule
- **category** (string, required): Category ID from `rule_categories`
- **name** (string, required): Human-readable rule name
- **description** (string, required): Detailed description of the rule
- **severity** (string, required): One of "critical", "warning", "info"
- **building_types** (array, required): List of applicable building types

### Condition Types

Rules support different condition types for validation:

#### 1. Minimum/Maximum Value Conditions

```json
{
  "condition": {
    "type": "minimum_value",  // or "maximum_value"
    "field": "path.to.field",
    "operator": ">=",  // or "<=", ">", "<", "==", "!="
    "value": 5.0,
    "unit": "meters"
  }
}
```

#### 2. Required Field Conditions

```json
{
  "condition": {
    "type": "required_field",
    "field": "path.to.field",
    "allowed_values": ["value1", "value2"]  // optional
  }
}
```

#### 3. Minimum Count Conditions

```json
{
  "condition": {
    "type": "minimum_count",
    "field": "array.field",
    "operator": ">=",
    "value": 2,
    "applies_when": {  // optional conditional application
      "field": "other.field",
      "operator": ">",
      "value": 1
    }
  }
}
```

#### 4. Area-based Conditions

```json
{
  "condition": {
    "type": "minimum_area",
    "field": "spaces[?(@.type=='bedroom')].area",  // JSONPath expression
    "operator": ">=",
    "value": 9.0,
    "unit": "square_meters"
  }
}
```

#### 5. Percentage Conditions

```json
{
  "condition": {
    "type": "minimum_percentage",
    "field": "spaces[?(@.type in ['bedroom', 'living_room'])].ventilation.natural",
    "operator": ">=",
    "value": 80,
    "unit": "percent"
  }
}
```

### Field Path Expressions

Field paths use dot notation to access nested properties in the design specification:

- `building_info.height` - Simple nested property
- `setbacks.front` - Nested object property
- `spaces[*].area` - Array element property (all elements)
- `spaces[?(@.type=='bedroom')].area` - JSONPath filter expression
- `structure.foundation_type` - Required field validation

### Violation Messages

Rules include templated violation messages that support variable substitution:

```json
{
  "violation_message": "Front setback must be at least {required_value} {unit}. Current value: {current_value} {unit}",
  "suggestion": "Increase front setback to meet minimum requirement"
}
```

Available template variables:
- `{required_value}` - The required/expected value
- `{current_value}` - The actual value found in the design
- `{unit}` - The unit of measurement
- `{allowed_values}` - List of allowed values (for required_field conditions)

## Severity Levels

Rules are classified by severity level:

### Critical
- **blocks_approval**: true
- **color**: red
- **priority**: 1
- Violations prevent design approval and must be fixed

### Warning
- **blocks_approval**: false
- **color**: orange
- **priority**: 2
- Violations are flagged but don't prevent approval

### Info
- **blocks_approval**: false
- **color**: blue
- **priority**: 3
- Informational notices for best practices

## Building Types

Rules can be applied to specific building types:

- `residential` - Single-family homes, apartments, condos
- `commercial` - Offices, retail, restaurants
- `industrial` - Warehouses, factories, manufacturing
- `institutional` - Schools, hospitals, government buildings
- `mixed_use` - Buildings with multiple use types

## Design Specification Structure

Rules validate against the design specification JSON structure:

```json
{
  "building_info": {
    "type": "residential",
    "subtype": "single_family",
    "total_area": 250.5,
    "num_floors": 2,
    "height": 7.5
  },
  "structure": {
    "foundation_type": "slab",
    "wall_material": "concrete_block",
    "roof_type": "pitched"
  },
  "setbacks": {
    "front": 5.0,
    "rear": 3.0,
    "side": 2.0
  },
  "spaces": [
    {
      "name": "Living Room",
      "type": "living_room",
      "area": 35.0,
      "floor": 1,
      "dimensions": {
        "length": 7.0,
        "width": 5.0,
        "height": 3.0
      },
      "ventilation": {
        "natural": true
      }
    }
  ],
  "fire_safety": {
    "exits": 2,
    "smoke_detectors": true
  },
  "accessibility": {
    "accessible_entrance": true,
    "accessible_bathroom": true
  },
  "environmental": {
    "energy_rating": 4,
    "insulation_type": "bulk"
  }
}
```

## Validation Configuration

The `validation_config` section controls validation behavior:

```json
{
  "validation_config": {
    "timeout_seconds": 10,
    "max_violations_per_rule": 10,
    "severity_levels": {
      "critical": {
        "blocks_approval": true,
        "color": "red",
        "priority": 1
      }
    }
  }
}
```

## Adding New Rule Sets

To add a new building code rule set:

1. Create a new JSON file in this directory
2. Follow the structure outlined above
3. Test the rule set with sample designs
4. Update the ValidationService configuration to include the new rule set

## Example Rule Sets

- `Standard_Building_Code_2020.json` - General building code for Kenya
- `Nairobi_City_Code_2021.json` - City-specific requirements (future)
- `Green_Building_Standards.json` - Sustainability requirements (future)

## Validation Process

The ValidationService loads rule sets and applies them to design specifications:

1. Load rule set JSON file
2. Filter rules by building type
3. Evaluate each rule condition against design data
4. Collect violations and warnings
5. Generate validation report with suggestions

## Testing Rules

Rule sets should be tested with various design scenarios:

- Compliant designs (should pass all critical rules)
- Non-compliant designs (should catch violations)
- Edge cases (boundary values, missing fields)
- Different building types and configurations

## Performance Considerations

- Rule evaluation should complete within 10 seconds
- Complex JSONPath expressions may impact performance
- Consider caching rule sets in memory
- Limit the number of violations per rule to prevent excessive output