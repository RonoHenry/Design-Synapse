"""
Project API routes.
"""

from typing import List

import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.base import ValidationError

from ..schemas.project import (
    Project,
    ProjectCreate,
    ProjectStatusUpdate,
    ProjectUpdate,
)
from ....core.config import settings
from ....core.exceptions import ProjectNotFoundError
from ....infrastructure.database import get_db
from ....models import Project as ProjectModel

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
) -> Project:
    """Create a new project."""
    project = ProjectModel(**project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> Project:
    """Get a specific project by ID."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)
    return project


@router.get("/", response_model=List[Project])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[Project]:
    """List all projects with pagination."""
    projects = (
        db.query(ProjectModel)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return projects


@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
) -> Project:
    """Update a project."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)

    for key, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}/status", response_model=Project)
def update_project_status(
    project_id: int,
    status_data: ProjectStatusUpdate,
    db: Session = Depends(get_db),
) -> Project:
    """Update a project's status."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)

    project.status = status_data.status
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a project."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(project_id)

    db.delete(project)
    db.commit()