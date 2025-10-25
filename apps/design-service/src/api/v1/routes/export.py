"""
Design export API routes.

This module provides REST API endpoints for exporting designs
in various formats (JSON, PDF, IFC).
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field

from ....infrastructure.database import get_db
from ....repositories.design_repository import DesignRepository
from ....services.project_client import ProjectClient, ProjectAccessDeniedError
from ...dependencies import CurrentUserId, get_current_user_id

router = APIRouter(prefix="/designs", tags=["export"])


class ExportRequest(BaseModel):
    """Request schema for design export."""
    format: str = Field(..., description="Export format: json, pdf, or ifc")


def get_design_repository(db: Session = Depends(get_db)) -> DesignRepository:
    """Dependency to get design repository instance."""
    return DesignRepository(db)


def get_project_client() -> ProjectClient:
    """Dependency to get project client instance."""
    return ProjectClient()


@router.post(
    "/{design_id}/export",
    summary="Export a design",
    description="Export a design in the specified format (JSON, PDF, or IFC)",
)
async def export_design(
    design_id: int,
    request: ExportRequest,
    user_id: CurrentUserId,
    db: Session = Depends(get_db),
    repository: DesignRepository = Depends(get_design_repository),
    project_client: ProjectClient = Depends(get_project_client),
):
    """Export a design in the specified format."""
    export_format = request.format.lower()
    
    supported_formats = ["json", "pdf", "ifc"]
    if export_format not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{request.format}'. Supported formats: {', '.join(supported_formats)}",
        )
    
    from ....models.design import Design
    design = db.query(Design).options(
        joinedload(Design.validations),
        joinedload(Design.optimizations),
        joinedload(Design.files),
        joinedload(Design.comments),
    ).filter(
        Design.id == design_id,
        Design.is_archived == False
    ).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found",
        )
    
    try:
        await project_client.verify_project_access(
            project_id=design.project_id,
            user_id=user_id,
        )
    except ProjectAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {design.project_id}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )
    
    try:
        if export_format == "json":
            return export_as_json(design)
        elif export_format == "pdf":
            return export_as_pdf(design)
        elif export_format == "ifc":
            return export_as_ifc(design)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )



def export_as_json(design) -> Dict[str, Any]:
    """Export design as JSON with all related data."""
    return {
        "design": {
            "id": design.id,
            "project_id": design.project_id,
            "name": design.name,
            "description": design.description,
            "specification": design.specification,
            "building_type": design.building_type,
            "total_area": design.total_area,
            "num_floors": design.num_floors,
            "materials": design.materials,
            "generation_prompt": design.generation_prompt,
            "confidence_score": design.confidence_score,
            "ai_model_version": design.ai_model_version,
            "version": design.version,
            "parent_design_id": design.parent_design_id,
            "status": design.status,
            "is_archived": design.is_archived,
            "created_by": design.created_by,
            "created_at": design.created_at.isoformat() if design.created_at else None,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None,
        },
        "validations": [
            {
                "id": v.id,
                "validation_type": v.validation_type,
                "rule_set": v.rule_set,
                "is_compliant": v.is_compliant,
                "violations": v.violations,
                "warnings": v.warnings,
                "validated_at": v.validated_at.isoformat() if v.validated_at else None,
                "validated_by": v.validated_by,
            }
            for v in design.validations
        ],
        "optimizations": [
            {
                "id": o.id,
                "optimization_type": o.optimization_type,
                "title": o.title,
                "description": o.description,
                "estimated_cost_impact": o.estimated_cost_impact,
                "implementation_difficulty": o.implementation_difficulty,
                "priority": o.priority,
                "status": o.status,
                "applied_at": o.applied_at.isoformat() if o.applied_at else None,
                "applied_by": o.applied_by,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in design.optimizations
        ],
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "storage_path": f.storage_path,
                "description": f.description,
                "uploaded_by": f.uploaded_by,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in design.files
        ],
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "position_x": c.position_x,
                "position_y": c.position_y,
                "position_z": c.position_z,
                "created_by": c.created_by,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "is_edited": c.is_edited,
            }
            for c in design.comments
        ],
        "metadata": {
            "format": "json",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
        }
    }



def export_as_pdf(design) -> Response:
    """Export design as PDF document."""
    # Convert design to dictionary for PDF generation
    design_dict = {
        "id": design.id,
        "name": design.name,
        "description": design.description,
        "specification": design.specification,
        "building_type": design.building_type,
        "total_area": design.total_area,
        "num_floors": design.num_floors,
        "status": design.status,
        "version": design.version,
        "validations": [
            {
                "validation_type": v.validation_type,
                "is_compliant": v.is_compliant,
                "violations": v.violations,
                "warnings": v.warnings,
            }
            for v in design.validations
        ]
    }
    
    pdf_content = generate_pdf_document(design_dict)
    
    filename = f"{design.name.replace(' ', '-')}.pdf"
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def export_as_ifc(design) -> Response:
    """Export design as IFC (Building Information Model) file."""
    # Convert design to dictionary for IFC generation
    design_dict = {
        "id": design.id,
        "name": design.name,
        "description": design.description,
        "specification": design.specification,
        "building_type": design.building_type,
        "created_by": design.created_by,
    }
    
    ifc_content = generate_ifc_file(design_dict)
    
    filename = f"{design.name.replace(' ', '-')}.ifc"
    
    return Response(
        content=ifc_content,
        media_type="application/x-step",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )



def generate_pdf_document(design: Dict[str, Any]) -> bytes:
    """
    Generate a formatted PDF document from design data.
    
    This is a simplified implementation. In production, you would use
    a library like ReportLab or WeasyPrint for professional PDF generation.
    
    Args:
        design: Dictionary containing design data
    
    Returns:
        PDF content as bytes
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
    )
    
    story.append(Paragraph(f"Design: {design['name']}", title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    if design.get('description'):
        story.append(Paragraph(f"<b>Description:</b> {design['description']}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
    
    story.append(Paragraph("Design Information", heading_style))
    info_data = [
        ["Building Type:", design.get('building_type', 'N/A')],
        ["Total Area:", f"{design['total_area']} m²" if design.get('total_area') else "N/A"],
        ["Number of Floors:", str(design['num_floors']) if design.get('num_floors') else "N/A"],
        ["Status:", design.get('status', 'N/A')],
        ["Version:", str(design.get('version', 'N/A'))],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))
    
    if design.get('specification'):
        story.append(Paragraph("Design Specification", heading_style))
        spec_text = str(design['specification'])[:500]
        story.append(Paragraph(spec_text, styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
    
    if design.get('validations'):
        story.append(Paragraph("Validation Results", heading_style))
        for validation in design['validations']:
            status_text = "✓ Compliant" if validation['is_compliant'] else "✗ Non-Compliant"
            story.append(Paragraph(f"<b>{validation['validation_type']}:</b> {status_text}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
    
    story.append(Spacer(1, 0.3 * inch))
    now = datetime.now(timezone.utc)
    story.append(Paragraph(f"<i>Generated on {now.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()



def generate_ifc_file(design: Dict[str, Any]) -> bytes:
    """
    Generate an IFC (Industry Foundation Classes) file from design data.
    
    This is a simplified implementation. In production, you would use
    a library like ifcopenshell for proper IFC file generation.
    
    Args:
        design: Dictionary containing design data
    
    Returns:
        IFC content as bytes
    """
    import json
    
    now = datetime.now(timezone.utc)
    ifc_header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('{design["name"]}.ifc','{now.isoformat()}',('DesignSynapse'),('DesignSynapse Platform'),'DesignSynapse Exporter','DesignSynapse v1.0','');
FILE_SCHEMA(('IFC4'));
ENDSEC;

DATA;
"""
    
    now_timestamp = int(now.timestamp())
    ifc_project = f"""#1=IFCPROJECT('{design["id"]}',#2,'Design: {design["name"]}','{design.get("description") or ""}',$,$,$,$,#3);
#2=IFCOWNERHISTORY(#4,#5,$,.ADDED.,$,$,$,{now_timestamp});
#3=IFCUNITASSIGNMENT((#6,#7,#8));
#4=IFCPERSON($,'{design["created_by"]}',$,$,$,$,$,$);
#5=IFCORGANIZATION($,'DesignSynapse',$,$,$);
#6=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#7=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#8=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
"""
    
    building_info = design["specification"].get('building_info', {})
    building_type = building_info.get('type', design.get("building_type", "unknown"))
    num_floors = building_info.get('num_floors', 1)
    
    ifc_building = f"""#10=IFCBUILDING('{design["id"]}-building',#2,'{design["name"]}','{building_type}',$,#11,$,$,.ELEMENT.,$,$,$);
#11=IFCLOCALPLACEMENT($,#12);
#12=IFCAXIS2PLACEMENT3D(#13,$,$);
#13=IFCCARTESIANPOINT((0.,0.,0.));
"""
    
    ifc_spaces = ""
    spaces = design["specification"].get('spaces', [])
    space_id = 20
    for idx, space in enumerate(spaces):
        space_name = space.get('name', f'Space {idx+1}')
        space_area = space.get('area', 0)
        floor = space.get('floor', 1)
        
        ifc_spaces += f"""#{space_id}=IFCSPACE('{design["id"]}-space-{idx}',#2,'{space_name}','Floor {floor}',$,#11,$,$,.ELEMENT.,{space_area},$);
"""
        space_id += 1
    
    ifc_footer = """ENDSEC;
END-ISO-10303-21;
"""
    
    ifc_content = ifc_header + ifc_project + ifc_building + ifc_spaces + ifc_footer
    
    return ifc_content.encode('utf-8')
