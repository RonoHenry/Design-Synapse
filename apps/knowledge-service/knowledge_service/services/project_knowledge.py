"""Integration with the project service."""

from datetime import datetime
from typing import Dict, List, Optional

import httpx
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..core.llm import get_llm_service
from ..core.vector_search import get_vector_search_service
from ..models import Citation, Resource


class ProjectKnowledgeService:
    """Service for integrating knowledge resources with projects."""

    def __init__(self):
        """Initialize the service."""
        self.project_service_url = "http://project-service:8000"
        self.llm_service = get_llm_service()
        self.vector_service = get_vector_search_service()

    def _apply_database_filters(
        self,
        query_builder,
        resource_type: str = "all",
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        license_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_file_size: Optional[int] = None,
        max_file_size: Optional[int] = None,
        has_doi: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
    ):
        """Apply database-level filters to a query builder."""

        # Resource type filter
        if resource_type != "all":
            query_builder = query_builder.filter(Resource.content_type == resource_type)

        # Author filter (case-insensitive partial match)
        if author:
            query_builder = query_builder.filter(
                func.lower(Resource.author).contains(func.lower(author))
            )

        # Source platform filter (case-insensitive partial match)
        if source_platform:
            query_builder = query_builder.filter(
                func.lower(Resource.source_platform).contains(
                    func.lower(source_platform)
                )
            )

        # License type filter (case-insensitive partial match)
        if license_type:
            query_builder = query_builder.filter(
                func.lower(Resource.license_type).contains(func.lower(license_type))
            )

        # Date range filters
        if date_from:
            query_builder = query_builder.filter(Resource.publication_date >= date_from)
        if date_to:
            query_builder = query_builder.filter(Resource.publication_date <= date_to)

        # File size filters
        if min_file_size is not None:
            query_builder = query_builder.filter(Resource.file_size >= min_file_size)
        if max_file_size is not None:
            query_builder = query_builder.filter(Resource.file_size <= max_file_size)

        # DOI filter
        if has_doi is not None:
            if has_doi:
                query_builder = query_builder.filter(Resource.doi.isnot(None))
            else:
                query_builder = query_builder.filter(Resource.doi.is_(None))

        # Keywords filter (search in keywords JSON array)
        if keywords:
            for keyword in keywords:
                query_builder = query_builder.filter(
                    func.json_contains(Resource.keywords, f'"{keyword}"')
                )

        return query_builder

    def _sort_results(
        self, results: List[Dict], sort_by: str, sort_order: str
    ) -> List[Dict]:
        """Sort results based on the specified criteria."""
        reverse = sort_order.lower() == "desc"

        if sort_by == "relevance":
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=reverse)
        elif sort_by == "date":
            results.sort(
                key=lambda x: x.get("publication_date")
                or ("" if reverse else "9999-12-31"),
                reverse=reverse,
            )
        elif sort_by == "title":
            results.sort(key=lambda x: x.get("title", "").lower(), reverse=reverse)
        elif sort_by == "type":
            results.sort(key=lambda x: x.get("content_type", ""), reverse=reverse)
        elif sort_by == "author":
            results.sort(
                key=lambda x: x.get("author", "").lower()
                if x.get("author")
                else ("" if reverse else "zzz"),
                reverse=reverse,
            )
        elif sort_by == "file_size":
            results.sort(
                key=lambda x: x.get("file_size", 0)
                if x.get("file_size") is not None
                else (0 if reverse else float("inf")),
                reverse=reverse,
            )

        return results

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
        self, db: Session, resource_id: int, project_id: int, context: str, user_id: int
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
            created_by=user_id,
        )
        db.add(citation)
        db.commit()
        db.refresh(citation)

        return citation

    async def get_project_resources(self, db: Session, project_id: int) -> List[Dict]:
        """
        Get all knowledge resources linked to a project.

        Args:
            db: Database session
            project_id: ID of the project

        Returns:
            List of resources with citation information
        """
        citations = db.query(Citation).filter(Citation.project_id == project_id).all()

        resources = []
        for citation in citations:
            resource = citation.resource
            resources.append(
                {
                    "id": resource.id,
                    "title": resource.title,
                    "description": resource.description,
                    "content_type": resource.content_type,
                    "citation_context": citation.context,
                    "cited_at": citation.created_at.isoformat(),
                    "cited_by": citation.created_by,
                }
            )

        return resources

    async def search_project_knowledge(
        self,
        db: Session,
        project_id: int,
        query: str,
        include_global: bool = True,
        resource_type: str = "all",
        min_score: float = 0.0,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        license_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_file_size: Optional[int] = None,
        max_file_size: Optional[int] = None,
        has_doi: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        Search for knowledge resources in project context using vector search.

        Args:
            db: Database session
            project_id: ID of the project
            query: Search query
            include_global: Whether to include resources not yet cited in project
            resource_type: Type of resource to filter by
            min_score: Minimum relevance score threshold
            sort_by: Sort results by (relevance, date, title, type, author, file_size)
            sort_order: Sort order (asc/desc)
            tags: Filter by resource tags
            author: Filter by author name
            source_platform: Filter by source platform
            license_type: Filter by license type
            date_from: Filter by publication date from
            date_to: Filter by publication date to
            min_file_size: Minimum file size in bytes
            max_file_size: Maximum file size in bytes
            has_doi: Filter resources with/without DOI
            keywords: Filter by keywords
            page: Page number for pagination
            page_size: Results per page

        Returns:
            Search results with project and global resources
        """
        # Get project's existing resources
        project_resources = await self.get_project_resources(db, project_id)

        # Search all resources if include_global is True
        global_resources = []
        if include_global:
            # Use vector search for semantic similarity
            try:
                # Build metadata filter for resource type if specified
                filter_metadata = {}
                if resource_type != "all":
                    filter_metadata["content_type"] = resource_type

                # Get vector search results
                vector_results = await self.vector_service.search_resources(
                    query=query,
                    filter_metadata=filter_metadata if filter_metadata else None,
                    top_k=min(page_size * 5, 200),  # Get more results for filtering
                )

                # Get cited resource IDs to exclude
                cited_ids = {r["id"] for r in project_resources}

                # Build database query with filters for additional filtering
                resource_query = db.query(Resource)
                resource_query = self._apply_database_filters(
                    resource_query,
                    resource_type=resource_type,
                    author=author,
                    source_platform=source_platform,
                    license_type=license_type,
                    date_from=date_from,
                    date_to=date_to,
                    min_file_size=min_file_size,
                    max_file_size=max_file_size,
                    has_doi=has_doi,
                    keywords=keywords,
                )

                # Get filtered resource IDs for efficient lookup
                filtered_resource_ids = {r.id for r in resource_query.all()}

                # Process vector search results
                for result in vector_results:
                    resource_id = result["resource_id"]
                    score = result["score"]

                    # Skip if already cited in project, below threshold, or doesn't match filters
                    if (
                        resource_id in cited_ids
                        or score < min_score
                        or resource_id not in filtered_resource_ids
                    ):
                        continue

                    # Get resource details from database
                    resource = (
                        db.query(Resource).filter(Resource.id == resource_id).first()
                    )
                    if resource:
                        global_resources.append(
                            {
                                "id": resource.id,
                                "title": resource.title,
                                "description": resource.description,
                                "content_type": resource.content_type,
                                "source_url": resource.source_url,
                                "source_platform": resource.source_platform,
                                "author": resource.author,
                                "publication_date": resource.publication_date.isoformat()
                                if resource.publication_date
                                else None,
                                "doi": resource.doi,
                                "license_type": resource.license_type,
                                "file_size": resource.file_size,
                                "keywords": resource.keywords,
                                "relevance_score": score,
                                "summary": resource.summary,
                            }
                        )

            except Exception as e:
                # Fallback to LLM-based search if vector search fails
                resource_query = db.query(Resource).filter(
                    Resource.id.notin_([r["id"] for r in project_resources])
                )

                # Apply database filters
                resource_query = self._apply_database_filters(
                    resource_query,
                    resource_type=resource_type,
                    author=author,
                    source_platform=source_platform,
                    license_type=license_type,
                    date_from=date_from,
                    date_to=date_to,
                    min_file_size=min_file_size,
                    max_file_size=max_file_size,
                    has_doi=has_doi,
                    keywords=keywords,
                )

                resources = resource_query.all()

                for resource in resources:
                    relevance = await self.llm_service.compare_similarity(
                        query, f"{resource.title}\n{resource.description}"
                    )
                    if relevance >= min_score:
                        global_resources.append(
                            {
                                "id": resource.id,
                                "title": resource.title,
                                "description": resource.description,
                                "content_type": resource.content_type,
                                "source_url": resource.source_url,
                                "source_platform": resource.source_platform,
                                "author": resource.author,
                                "publication_date": resource.publication_date.isoformat()
                                if resource.publication_date
                                else None,
                                "doi": resource.doi,
                                "license_type": resource.license_type,
                                "file_size": resource.file_size,
                                "keywords": resource.keywords,
                                "relevance_score": relevance,
                                "summary": resource.summary,
                            }
                        )

        # Sort results
        global_resources = self._sort_results(global_resources, sort_by, sort_order)

        # Paginate global resources
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_global = global_resources[start_idx:end_idx]

        return {
            "project_resources": project_resources,
            "global_resources": paginated_global,
            "total_global": len(global_resources),
            "page": page,
            "page_size": page_size,
        }

    async def get_recommendations(
        self,
        db: Session,
        project_id: int,
        resource_type: str = "all",
        min_score: float = 0.3,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        license_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_file_size: Optional[int] = None,
        max_file_size: Optional[int] = None,
        has_doi: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        Get knowledge resource recommendations for a project using vector search.

        Args:
            db: Database session
            project_id: ID of the project
            resource_type: Type of resource to filter by
            min_score: Minimum relevance score threshold
            sort_by: Sort results by (relevance, date, title, type, author, file_size)
            sort_order: Sort order (asc/desc)
            tags: Filter by resource tags
            author: Filter by author name
            source_platform: Filter by source platform
            license_type: Filter by license type
            date_from: Filter by publication date from
            date_to: Filter by publication date to
            min_file_size: Minimum file size in bytes
            max_file_size: Maximum file size in bytes
            has_doi: Filter resources with/without DOI
            keywords: Filter by keywords
            page: Page number for pagination
            page_size: Results per page

        Returns:
            Dictionary with recommended resources and metadata
        """
        # Get project details to understand context
        project = await self.validate_project(project_id)
        project_text = f"{project['name']}\n{project['description']}"

        # Get resources not yet cited in project
        cited_ids = {
            c.resource_id
            for c in db.query(Citation).filter(Citation.project_id == project_id).all()
        }

        recommendations = []

        try:
            # Use vector search for semantic similarity
            filter_metadata = {}
            if resource_type != "all":
                filter_metadata["content_type"] = resource_type

            # Get vector search results based on project context
            vector_results = await self.vector_service.search_resources(
                query=project_text,
                filter_metadata=filter_metadata if filter_metadata else None,
                top_k=min(page_size * 5, 200),  # Get more results for filtering
            )

            # Build database query with filters for additional filtering
            resource_query = db.query(Resource).filter(Resource.id.notin_(cited_ids))
            resource_query = self._apply_database_filters(
                resource_query,
                resource_type=resource_type,
                author=author,
                source_platform=source_platform,
                license_type=license_type,
                date_from=date_from,
                date_to=date_to,
                min_file_size=min_file_size,
                max_file_size=max_file_size,
                has_doi=has_doi,
                keywords=keywords,
            )

            # Get filtered resource IDs for efficient lookup
            filtered_resource_ids = {r.id for r in resource_query.all()}

            # Process vector search results
            for result in vector_results:
                resource_id = result["resource_id"]
                score = result["score"]

                # Skip if already cited in project, below threshold, or doesn't match filters
                if (
                    resource_id in cited_ids
                    or score < min_score
                    or resource_id not in filtered_resource_ids
                ):
                    continue

                # Get resource details from database
                resource = db.query(Resource).filter(Resource.id == resource_id).first()
                if resource:
                    recommendations.append(
                        {
                            "id": resource.id,
                            "title": resource.title,
                            "description": resource.description,
                            "content_type": resource.content_type,
                            "source_url": resource.source_url,
                            "source_platform": resource.source_platform,
                            "author": resource.author,
                            "publication_date": resource.publication_date.isoformat()
                            if resource.publication_date
                            else None,
                            "doi": resource.doi,
                            "license_type": resource.license_type,
                            "file_size": resource.file_size,
                            "keywords": resource.keywords,
                            "relevance_score": score,
                            "summary": resource.summary,
                        }
                    )

        except Exception as e:
            # Fallback to LLM-based recommendations if vector search fails
            resource_query = db.query(Resource).filter(Resource.id.notin_(cited_ids))

            # Apply database filters
            resource_query = self._apply_database_filters(
                resource_query,
                resource_type=resource_type,
                author=author,
                source_platform=source_platform,
                license_type=license_type,
                date_from=date_from,
                date_to=date_to,
                min_file_size=min_file_size,
                max_file_size=max_file_size,
                has_doi=has_doi,
                keywords=keywords,
            )

            candidates = resource_query.all()

            for resource in candidates:
                resource_text = f"{resource.title}\n{resource.description}"

                # Get similarity score
                relevance = await self.llm_service.compare_similarity(
                    project_text, resource_text
                )

                if relevance >= min_score:
                    recommendations.append(
                        {
                            "id": resource.id,
                            "title": resource.title,
                            "description": resource.description,
                            "content_type": resource.content_type,
                            "source_url": resource.source_url,
                            "source_platform": resource.source_platform,
                            "author": resource.author,
                            "publication_date": resource.publication_date.isoformat()
                            if resource.publication_date
                            else None,
                            "doi": resource.doi,
                            "license_type": resource.license_type,
                            "file_size": resource.file_size,
                            "keywords": resource.keywords,
                            "relevance_score": relevance,
                            "summary": resource.summary,
                        }
                    )

        # Sort results
        recommendations = self._sort_results(recommendations, sort_by, sort_order)

        # Paginate results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_recommendations = recommendations[start_idx:end_idx]

        return {
            "total": len(recommendations),
            "page": page,
            "page_size": page_size,
            "results": paginated_recommendations,
        }

    def get_citation_analytics(self, db: Session, project_id: int) -> Dict:
        """
        Get analytics about knowledge resource usage in a project.

        Args:
            db: Database session
            project_id: ID of the project

        Returns:
            Dictionary with citation statistics
        """
        citations = db.query(Citation).filter(Citation.project_id == project_id).all()

        # Get citation counts by resource
        resource_counts = {}
        for citation in citations:
            resource_id = citation.resource_id
            if resource_id not in resource_counts:
                resource_counts[resource_id] = {
                    "count": 0,
                    "title": citation.resource.title,
                    "last_cited": citation.created_at,
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
                    "last_cited": info["last_cited"].isoformat(),
                }
                for rid, info in resource_counts.items()
            ],
        }

    async def search_global(
        self,
        db: Session,
        query: str,
        resource_type: str = "all",
        min_score: float = 0.0,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        source_platform: Optional[str] = None,
        license_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_file_size: Optional[int] = None,
        max_file_size: Optional[int] = None,
        has_doi: Optional[bool] = None,
        keywords: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """
        Search all knowledge resources globally using vector search.

        Args:
            db: Database session
            query: Search query string
            resource_type: Type of resource to filter by
            min_score: Minimum relevance score threshold
            sort_by: Sort results by (relevance, date, title, type, author, file_size)
            sort_order: Sort order (asc/desc)
            tags: Filter by resource tags
            author: Filter by author name
            source_platform: Filter by source platform
            license_type: Filter by license type
            date_from: Filter by publication date from
            date_to: Filter by publication date to
            min_file_size: Minimum file size in bytes
            max_file_size: Maximum file size in bytes
            has_doi: Filter resources with/without DOI
            keywords: Filter by keywords
            page: Page number for pagination
            page_size: Results per page

        Returns:
            Dictionary with search results and metadata
        """
        scored_results = []

        try:
            # Use vector search for semantic similarity
            filter_metadata = {}
            if resource_type != "all":
                filter_metadata["content_type"] = resource_type

            # Get vector search results
            vector_results = await self.vector_service.search_resources(
                query=query,
                filter_metadata=filter_metadata if filter_metadata else None,
                top_k=min(
                    page_size * 10, 300
                ),  # Get more results for sorting and filtering
            )

            # Build database query with filters for additional filtering
            resource_query = db.query(Resource)
            resource_query = self._apply_database_filters(
                resource_query,
                resource_type=resource_type,
                author=author,
                source_platform=source_platform,
                license_type=license_type,
                date_from=date_from,
                date_to=date_to,
                min_file_size=min_file_size,
                max_file_size=max_file_size,
                has_doi=has_doi,
                keywords=keywords,
            )

            # Get filtered resource IDs for efficient lookup
            filtered_resource_ids = {r.id for r in resource_query.all()}

            # Process vector search results
            for result in vector_results:
                resource_id = result["resource_id"]
                score = result["score"]

                # Skip if below threshold or doesn't match filters
                if score < min_score or resource_id not in filtered_resource_ids:
                    continue

                # Get resource details from database
                resource = db.query(Resource).filter(Resource.id == resource_id).first()
                if resource:
                    scored_results.append(
                        {
                            "id": resource.id,
                            "title": resource.title,
                            "description": resource.description,
                            "content_type": resource.content_type,
                            "source_url": resource.source_url,
                            "source_platform": resource.source_platform,
                            "author": resource.author,
                            "publication_date": resource.publication_date.isoformat()
                            if resource.publication_date
                            else None,
                            "doi": resource.doi,
                            "license_type": resource.license_type,
                            "file_size": resource.file_size,
                            "keywords": resource.keywords,
                            "relevance_score": score,
                            "summary": resource.summary,
                        }
                    )

        except Exception as e:
            # Fallback to LLM-based search if vector search fails
            resource_query = db.query(Resource)

            # Apply database filters
            resource_query = self._apply_database_filters(
                resource_query,
                resource_type=resource_type,
                author=author,
                source_platform=source_platform,
                license_type=license_type,
                date_from=date_from,
                date_to=date_to,
                min_file_size=min_file_size,
                max_file_size=max_file_size,
                has_doi=has_doi,
                keywords=keywords,
            )

            resources = resource_query.all()

            for resource in resources:
                # Create combined text for similarity comparison
                resource_text = f"{resource.title}\n{resource.description}"
                if resource.summary:
                    resource_text += f"\n{resource.summary}"

                # Use LLM service for semantic similarity
                relevance = await self.llm_service.compare_similarity(
                    query, resource_text
                )

                if relevance >= min_score:
                    scored_results.append(
                        {
                            "id": resource.id,
                            "title": resource.title,
                            "description": resource.description,
                            "content_type": resource.content_type,
                            "source_url": resource.source_url,
                            "source_platform": resource.source_platform,
                            "author": resource.author,
                            "publication_date": resource.publication_date.isoformat()
                            if resource.publication_date
                            else None,
                            "doi": resource.doi,
                            "license_type": resource.license_type,
                            "file_size": resource.file_size,
                            "keywords": resource.keywords,
                            "relevance_score": relevance,
                            "summary": resource.summary,
                        }
                    )

        # Sort results
        scored_results = self._sort_results(scored_results, sort_by, sort_order)

        # Paginate results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = scored_results[start_idx:end_idx]

        return {
            "total": len(scored_results),
            "page": page,
            "page_size": page_size,
            "results": paginated_results,
        }
