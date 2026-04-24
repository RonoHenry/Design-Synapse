# Automatic Recalculation System

## Overview

The Engineering Service now supports automatic recalculation of dependent calculations. When a calculation's inputs change, all calculations that depend on it are automatically recalculated, ensuring data consistency across the system.

## Architecture

### Components

1. **CalculationDependency Model** - Tracks dependencies between calculation sheets
2. **CalculationDependencyRepository** - Manages dependency data access
3. **RecalculationService** - Orchestrates recalculation cascades
4. **StructuralCalculationService** - Integrated with recalculation logic

### Dependency Tracking

Dependencies are tracked at the calculation sheet level. When calculation A depends on calculation B:
- Changing B triggers recalculation of A
- The system prevents circular dependencies
- Cascading updates propagate through the entire dependency chain

## Usage Examples

### Adding a Dependency

```python
from src.services.structural_calculation_service import StructuralCalculationService

# Initialize service
service = StructuralCalculationService(db_session)

# Add dependency: beam design depends on load calculation
await service.add_calculation_dependency(
    source_calculation_id=beam_calc_id,  # The dependent calculation
    target_calculation_id=load_calc_id,  # The calculation being depended upon
    dependency_type="load_input",
    user_id="user123",
    dependent_field="inputs.loads.dead_load",
    source_field="outputs.total_load"
)
```

### Updating Inputs with Automatic Recalculation

```python
# Update load calculation inputs
# This will automatically recalculate the beam design
await service.update_calculation_inputs(
    calculation_id=load_calc_id,
    new_inputs={
        "building_data": {
            "height": 25.0,  # Changed from 20.0
            "width": 50.0,
            "length": 100.0
        }
    },
    user_id="user123",
    trigger_recalculation=True  # Default is True
)
```

### Querying Dependencies

```python
# Get all calculations that depend on this one
dependents = await service.get_calculation_dependents(load_calc_id)

# Get all calculations that this one depends on
dependencies = await service.get_calculation_dependencies(beam_calc_id)

# Get the full dependency graph
graph = await service.get_dependency_graph(load_calc_id)
# Returns:
# {
#     "dependencies": [...],  # Calculations this one depends on
#     "dependents": [...]     # Calculations that depend on this one
# }
```

## Workflow Example

### Scenario: Load Calculation → Beam Design → Column Design

```python
# 1. Create load calculation
load_result = await service.calculate_loads(
    project_id="proj123",
    building_data={...},
    load_types=["dead", "live"],
    user_id="user123"
)
load_calc_id = load_result.calculation_id

# 2. Create beam design using load results
beam_result = await service.design_beam(
    project_id="proj123",
    loads={"uniform_load": load_result.total_load},
    span=20.0,
    material={...},
    user_id="user123"
)
beam_calc_id = beam_result.calculation_id

# 3. Add dependency: beam depends on loads
await service.add_calculation_dependency(
    source_calculation_id=beam_calc_id,
    target_calculation_id=load_calc_id,
    dependency_type="load_input",
    user_id="user123"
)

# 4. Create column design using beam reactions
column_result = await service.design_column(
    project_id="proj123",
    loads={"axial_load": beam_result.max_shear},
    length=120.0,
    material={...},
    geometry={...},
    user_id="user123"
)
column_calc_id = column_result.calculation_id

# 5. Add dependency: column depends on beam
await service.add_calculation_dependency(
    source_calculation_id=column_calc_id,
    target_calculation_id=beam_calc_id,
    dependency_type="load_input",
    user_id="user123"
)

# 6. Update load calculation
# This will automatically recalculate both beam AND column
await service.update_calculation_inputs(
    calculation_id=load_calc_id,
    new_inputs={"building_data": {"height": 30.0}},
    user_id="user123"
)
# Result: load_calc → beam_calc → column_calc all recalculated
```

## Dependency Types

Common dependency types include:

- `load_input` - Calculation depends on load values
- `material_property` - Calculation depends on material properties
- `geometry` - Calculation depends on geometric parameters
- `soil_property` - Foundation calculations depend on soil data
- `design_output` - Calculation depends on another design's output

## Circular Dependency Prevention

The system automatically prevents circular dependencies:

```python
# This will raise ValueError
await service.add_calculation_dependency(
    source_calculation_id=calc_a,
    target_calculation_id=calc_b,
    dependency_type="load_input",
    user_id="user123"
)

await service.add_calculation_dependency(
    source_calculation_id=calc_b,
    target_calculation_id=calc_a,  # Creates a cycle!
    dependency_type="load_input",
    user_id="user123"
)
# ValueError: Cannot add dependency: would create circular dependency
```

## Recalculation Behavior

### Automatic Recalculation

When a calculation is updated:
1. The system identifies all dependent calculations
2. Each dependent is recalculated using its stored inputs
3. The recalculation cascade propagates through the dependency chain
4. All affected calculations are marked as "approved" after successful recalculation

### Manual Control

You can disable automatic recalculation:

```python
await service.update_calculation_inputs(
    calculation_id=load_calc_id,
    new_inputs={...},
    user_id="user123",
    trigger_recalculation=False  # Don't trigger cascade
)
```

In this case, dependent calculations are marked as "draft" to indicate they need recalculation.

## Database Schema

### calculation_dependencies Table

```sql
CREATE TABLE calculation_dependencies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_calculation_id INT NOT NULL,  -- The dependent calculation
    target_calculation_id INT NOT NULL,  -- The calculation being depended upon
    dependency_type VARCHAR(100) NOT NULL,
    dependent_field VARCHAR(255),        -- Field in source that depends
    source_field VARCHAR(255),           -- Field in target that is depended upon
    created_at DATETIME NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    FOREIGN KEY (source_calculation_id) REFERENCES calculation_sheets(id) ON DELETE CASCADE,
    FOREIGN KEY (target_calculation_id) REFERENCES calculation_sheets(id) ON DELETE CASCADE,
    INDEX (source_calculation_id),
    INDEX (target_calculation_id)
);
```

## Migration

To apply the database migration:

```bash
cd apps/engineering-service
alembic upgrade head
```

## API Integration

The recalculation system is integrated into the service layer and can be exposed via API endpoints:

```python
# Example API endpoint
@router.post("/calculations/{calculation_id}/dependencies")
async def add_dependency(
    calculation_id: int,
    dependency: DependencyCreate,
    service: StructuralCalculationService = Depends(get_service)
):
    return await service.add_calculation_dependency(
        source_calculation_id=calculation_id,
        target_calculation_id=dependency.target_id,
        dependency_type=dependency.type,
        user_id=current_user.id
    )
```

## Performance Considerations

- **Cascade Depth**: Deep dependency chains may take longer to recalculate
- **Batch Updates**: Consider batching multiple input changes before triggering recalculation
- **Async Processing**: Recalculation is async and non-blocking
- **Error Handling**: Failed recalculations are logged but don't block the cascade

## Testing

Unit tests are provided in `tests/unit/services/test_recalculation_service.py`.

Run tests:
```bash
pytest apps/engineering-service/tests/unit/services/test_recalculation_service.py -v
```

## Future Enhancements

Potential improvements:
- Background job processing for large cascades
- Selective recalculation (only recalculate changed fields)
- Dependency visualization UI
- Recalculation history tracking
- Optimistic locking for concurrent updates
