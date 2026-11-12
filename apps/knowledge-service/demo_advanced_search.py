#!/usr/bin/env python3
"""
Demonstration script for advanced search filters and sorting functionality.

This script shows how the new advanced search features work:
- Advanced filters (author, date range, file size, DOI, keywords, etc.)
- Enhanced sorting options (by author, file size, etc.)
- Sort order control (ascending/descending)
"""

from datetime import datetime


def demo_advanced_search_filters():
    """Demonstrate the advanced search filter functionality."""

    print("=== Advanced Search Filters Demo ===\n")

    # Example 1: Search with author filter
    print("1. Search with Author Filter:")
    print("   GET /api/v1/search/global?query=machine learning&author=John Doe")
    print("   - Filters results to only show resources by 'John Doe'")
    print("   - Uses case-insensitive partial matching\n")

    # Example 2: Search with date range
    print("2. Search with Date Range Filter:")
    print(
        "   GET /api/v1/search/global?query=AI research&date_from=2023-01-01T00:00:00&date_to=2023-12-31T23:59:59"
    )
    print("   - Only returns resources published in 2023")
    print("   - Supports ISO datetime format\n")

    # Example 3: Search with file size constraints
    print("3. Search with File Size Filter:")
    print(
        "   GET /api/v1/search/global?query=documents&min_file_size=1024&max_file_size=1048576"
    )
    print("   - Only returns files between 1KB and 1MB")
    print("   - Useful for finding appropriately sized resources\n")

    # Example 4: Search for resources with DOI
    print("4. Search with DOI Filter:")
    print("   GET /api/v1/search/global?query=academic papers&has_doi=true")
    print("   - Only returns resources that have a DOI")
    print("   - Useful for finding peer-reviewed academic content\n")

    # Example 5: Search with keywords
    print("5. Search with Keywords Filter:")
    print(
        "   GET /api/v1/search/global?query=research&keywords=machine learning&keywords=neural networks"
    )
    print("   - Only returns resources tagged with specified keywords")
    print("   - Supports multiple keyword filters\n")

    # Example 6: Search with source platform
    print("6. Search with Source Platform Filter:")
    print("   GET /api/v1/search/global?query=papers&source_platform=MDPI")
    print("   - Only returns resources from specific platforms")
    print("   - Useful for filtering by trusted sources\n")

    # Example 7: Search with license type
    print("7. Search with License Filter:")
    print("   GET /api/v1/search/global?query=open access&license_type=CC BY")
    print("   - Only returns resources with specific license types")
    print("   - Helps ensure compliance with usage requirements\n")


def demo_advanced_sorting():
    """Demonstrate the advanced sorting functionality."""

    print("=== Advanced Sorting Options Demo ===\n")

    # Example 1: Sort by author
    print("1. Sort by Author (Ascending):")
    print("   GET /api/v1/search/global?query=research&sort_by=author&sort_order=asc")
    print("   - Results sorted alphabetically by author name")
    print("   - Resources without authors appear at the end\n")

    # Example 2: Sort by file size
    print("2. Sort by File Size (Descending):")
    print(
        "   GET /api/v1/search/global?query=documents&sort_by=file_size&sort_order=desc"
    )
    print("   - Largest files appear first")
    print("   - Useful for finding comprehensive resources\n")

    # Example 3: Sort by publication date
    print("3. Sort by Publication Date (Descending):")
    print(
        "   GET /api/v1/search/global?query=latest research&sort_by=date&sort_order=desc"
    )
    print("   - Most recent publications appear first")
    print("   - Default behavior for date sorting\n")

    # Example 4: Sort by content type
    print("4. Sort by Content Type:")
    print("   GET /api/v1/search/global?query=resources&sort_by=type&sort_order=asc")
    print("   - Groups results by content type (pdf, html, etc.)")
    print("   - Helps organize mixed content types\n")


def demo_combined_filters_and_sorting():
    """Demonstrate combining multiple filters with sorting."""

    print("=== Combined Filters and Sorting Demo ===\n")

    # Complex search example
    print("Complex Search Example:")
    print("GET /api/v1/search/global?")
    print("  query=BIM modeling&")
    print("  author=Jane Doe&")
    print("  source_platform=MDPI&")
    print("  license_type=CC BY&")
    print("  date_from=2023-01-01T00:00:00&")
    print("  min_file_size=1024&")
    print("  max_file_size=10485760&")
    print("  has_doi=true&")
    print("  keywords=BIM&keywords=modeling&")
    print("  sort_by=date&")
    print("  sort_order=desc&")
    print("  page=1&")
    print("  page_size=20")
    print("\nThis search will:")
    print("- Find resources about 'BIM modeling'")
    print("- By author 'Jane Doe'")
    print("- From MDPI platform")
    print("- With CC BY license")
    print("- Published in 2023 or later")
    print("- File size between 1KB and 10MB")
    print("- With DOI")
    print("- Tagged with 'BIM' and 'modeling' keywords")
    print("- Sorted by publication date (newest first)")
    print("- Return first 20 results\n")


def demo_project_search_filters():
    """Demonstrate project-specific search with filters."""

    print("=== Project Search with Filters Demo ===\n")

    print("Project Search Example:")
    print("GET /api/v1/search/project/123?")
    print("  query=sustainable design&")
    print("  include_global=true&")
    print("  author=Expert Author&")
    print("  resource_type=pdf&")
    print("  min_score=0.7&")
    print("  sort_by=relevance&")
    print("  sort_order=desc")
    print("\nThis search will:")
    print("- Search within project 123 context")
    print("- Include global resources not yet cited")
    print("- Filter by specific author")
    print("- Only PDF resources")
    print("- Minimum relevance score of 0.7")
    print("- Sorted by relevance (highest first)\n")


def demo_recommendations_filters():
    """Demonstrate recommendation filters."""

    print("=== Recommendation Filters Demo ===\n")

    print("Filtered Recommendations Example:")
    print("GET /api/v1/search/project/123/recommendations?")
    print("  resource_type=pdf&")
    print("  min_score=0.5&")
    print("  author=Research Expert&")
    print("  date_from=2022-01-01T00:00:00&")
    print("  has_doi=true&")
    print("  sort_by=date&")
    print("  sort_order=desc")
    print("\nThis will recommend:")
    print("- PDF resources only")
    print("- With relevance score >= 0.5")
    print("- By 'Research Expert'")
    print("- Published since 2022")
    print("- With DOI (peer-reviewed)")
    print("- Sorted by publication date (newest first)\n")


def main():
    """Run all demonstrations."""

    print("Knowledge Service Advanced Search & Sorting Features\n")
    print("=" * 60)

    demo_advanced_search_filters()
    demo_advanced_sorting()
    demo_combined_filters_and_sorting()
    demo_project_search_filters()
    demo_recommendations_filters()

    print("=" * 60)
    print("\nKey Benefits:")
    print("✓ Precise filtering by author, date, file size, DOI, keywords")
    print("✓ Flexible sorting by relevance, date, title, type, author, file size")
    print("✓ Ascending/descending sort order control")
    print("✓ Combines with existing search functionality")
    print("✓ Works across global search, project search, and recommendations")
    print("✓ Maintains backward compatibility with existing API")

    print("\nImplementation Features:")
    print("✓ Database-level filtering for performance")
    print("✓ Case-insensitive partial matching for text fields")
    print("✓ Graceful handling of missing values in sorting")
    print("✓ Efficient vector search integration")
    print("✓ Comprehensive error handling")


if __name__ == "__main__":
    main()
