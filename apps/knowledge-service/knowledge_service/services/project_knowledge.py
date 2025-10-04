"""Integration with the project service."""

from typing import Dict, List, Optional
from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from ..models import Resource, Citation
from ..core.llm import get_llm_service


class ProjectKnowledgeService:
    """Service for integrating knowledge resources with projects."""
    
    def __init__(self):
        """Initialize the service."""
        self.project_service_url = "http://project-service:8000"
        self.llm_service = get_llm_service()
    
    async def validate_project(self, project_id: int) -> Dict:
        """
        Validate that a project exists and is accessible.
        
        Args:
            project_id: The ID of the project to validate
            
        Returns:
            Project details if valid
            
        Raises:
            HTTPException if project is not found or inaccessible
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.project_service_url}/api/v1/projects/{project_id}"
            )
            response.raise_for_status()
            return response.json()
    
    async def add_citation(
        self,
        db: Session,
        resource_id: int,
        project_id: int,
        context: str,
        user_id: int
    ) -> Citation:
        """
        Add a citation of a knowledge resource to a project.
        
        Args:
            db: Database session
            resource_id: ID of the resource being cited
            project_id: ID of the project where it's cited
            context: How/where the resource is being used
            user_id: ID of the user creating the citation
            
        Returns:
            The created Citation object
        """
        # Validate project exists
        await self.validate_project(project_id)
        
        citation = Citation(
            resource_id=resource_id,
            project_id=project_id,
            context=context,
            created_by=user_id
        )
        db.add(citation)
        db.commit()
        db.refresh(citation)
        
        return citation
    
    async def get_project_resources(
        self,
        db: Session,
        project_id: int
    ) -> List[Dict]:
        """
        Get all knowledge resources linked to a project.
        
        Args:
            db: Database session
            project_id: ID of the project
            
        Returns:
            List of resources with citation information
        """
        citations = (
            db.query(Citation)
            .filter(Citation.project_id == project_id)
            .all()
        )
        
        resources = []
        for citation in citations:
            resource = citation.resource
            resources.append({
                "id": resource.id,
                "title": resource.title,
                "description": resource.description,
                "content_type": resource.content_type,
                "citation_context": citation.context,
                "cited_at": citation.created_at.isoformat(),
                "cited_by": citation.created_by
            })
            
        return resources
    
    async def search_project_knowledge(
        self,
        db: Session,
        project_id: int,
        query: str,
        include_global: bool = True
    ) -> Dict:
        """
        Search for knowledge resources in project context.
        
        Args:
            db: Database session
            project_id: ID of the project
            query: Search query
            include_global: Whether to include resources not yet cited in project
            
        Returns:
            Search results with project and global resources
        """
        # Get project's existing resources
        project_resources = await self.get_project_resources(db, project_id)
        
        # Search all resources if include_global is True
        global_resources = []
        if include_global:
            resources = (
                db.query(Resource)
                .filter(Resource.id.notin_([r["id"] for r in project_resources]))
                .all()
            )
            
            # Score relevance using LLM
            for resource in resources:
                relevance = await self.llm_service.compare_similarity(
                    query,
                    f"{resource.title}\n{resource.description}"
                )
                if relevance > 0.5:  # Only include reasonably relevant resources
                    global_resources.append({
                        "id": resource.id,
                        "title": resource.title,
                        "description": resource.description,
                        "content_type": resource.content_type,
                        "relevance_score": relevance
                    })
        
        return {
            "project_resources": project_resources,
            "global_resources": sorted(
                global_resources,
                key=lambda x: x["relevance_score"],
                reverse=True
            )
        }
    
    async def get_recommendations(
        self,
        db: Session,
        project_id: int
    ) -> List[Dict]:
        """
        Get knowledge resource recommendations for a project.
        
        Args:
            db: Database session
            project_id: ID of the project
            
        Returns:
            List of recommended resources with relevance scores
        """
        # Get project details to understand context
        project = await self.validate_project(project_id)
        project_text = f"{project['name']}\n{project['description']}"
        
        # Get resources not yet cited in project
        cited_ids = {
            c.resource_id for c in
            db.query(Citation)
            .filter(Citation.project_id == project_id)
            .all()
        }
        
        candidates = (
            db.query(Resource)
            .filter(Resource.id.notin_(cited_ids))
            .all()
        )
        
        # Score candidates
        recommendations = []
        for resource in candidates:
            resource_text = f"{resource.title}\n{resource.description}"
            
            # Get similarity score
            relevance = await self.llm_service.compare_similarity(
                project_text,
                resource_text
            )
            
            if relevance > 0.5:  # Only recommend reasonably relevant resources
                recommendations.append({
                    "id": resource.id,
                    "title": resource.title,
                    "description": resource.description,
                    "content_type": resource.content_type,
                    "relevance_score": relevance
                })
        
        # Sort by relevance
        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
        return recommendations[:10]  # Return top 10
    
    def get_citation_analytics(
        self,
        db: Session,
        project_id: int
    ) -> Dict:
        """
        Get analytics about knowledge resource usage in a project.
        
        Args:
            db: Database session
            project_id: ID of the project
            
        Returns:
            Dictionary with citation statistics
        """
        citations = (
            db.query(Citation)
            .filter(Citation.project_id == project_id)
            .all()
        )
        
        # Get citation counts by resource
        resource_counts = {}
        for citation in citations:
            resource_id = citation.resource_id
            if resource_id not in resource_counts:
                resource_counts[resource_id] = {
                    "count": 0,
                    "title": citation.resource.title,
                    "last_cited": citation.created_at
                }
            resource_counts[resource_id]["count"] += 1
            if citation.created_at > resource_counts[resource_id]["last_cited"]:
                resource_counts[resource_id]["last_cited"] = citation.created_at
        
        return {
            "total_citations": len(citations),
            "unique_resources": len(resource_counts),
            "resource_breakdown": [
                {
                    "resource_id": rid,
                    "title": info["title"],
                    "citation_count": info["count"],
                    "last_cited": info["last_cited"].isoformat()
                }
                for rid, info in resource_counts.items()
            ]
        }

    async def search_global(
        self,
        db: Session,
        query: str,
        resource_type: str = "all",
        min_score: float = 0.0,
        sort_by: str = "relevance",
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        Search all knowledge resources globally.
        
        Args:
            db: Database session
            query: Search query string
            resource_type: Type of resource to filter by
            min_score: Minimum relevance score threshold
            sort_by: Sort results by (relevance, date, title, type)
            tags: Filter by resource tags
            page: Page number for pagination
            page_size: Results per page
            
        Returns:
            Dictionary with search results and metadata
        """
        # Build base query
        resources_query = db.query(Resource)
        if resource_type != "all":
            resources_query = resources_query.filter(Resource.content_type == resource_type)

        # Get all matching resources
        resources = resources_query.all()
        
        # Score and filter results
        scored_results = []
        for resource in resources:
            # Create combined text for similarity comparison
            resource_text = f"{resource.title}\n{resource.description}"
            if resource.summary:
                resource_text += f"\n{resource.summary}"
            
            # Use LLM service for semantic similarity
            relevance = await self.llm_service.compare_similarity(query, resource_text)
            
            if relevance >= min_score:
                scored_results.append({
                    "id": resource.id,
                    "title": resource.title,
                    "description": resource.description,
                    "content_type": resource.content_type,
                    "source_url": resource.source_url,
                    "author": resource.author,
                    "publication_date": resource.publication_date.isoformat() if resource.publication_date else None,
                    "relevance_score": relevance
                })

        # Sort results
        if sort_by == "relevance":
            scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        elif sort_by == "date":
            scored_results.sort(key=lambda x: x.get("publication_date") or "", reverse=True)
        elif sort_by == "title":
            scored_results.sort(key=lambda x: x["title"])
        elif sort_by == "type":
            scored_results.sort(key=lambda x: x["content_type"])

        # Paginate results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = scored_results[start_idx:end_idx]

        return {
            "total": len(scored_results),
            "page": page,
            "page_size": page_size,
            "results": paginated_results
        }