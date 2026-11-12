# Vendor Service Design

## Overview

The Vendor Service is a marketplace microservice built on FastAPI with SQLAlchemy ORM, providing vendor management, product catalog, order processing, and reviews.

## Architecture

### Service Layers

```
API Layer (FastAPI Routes)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
Database Layer (TiDB)
```

## Components

### 1. Core Infrastructure
- Configuration management
- Database connection with TiDB
- Custom exceptions
- Authentication integration

### 2. Domain Models
- Vendor: Company profiles and verification
- Product: Catalog items with inventory
- Order: Purchase transactions
- OrderItem: Individual order line items
- Review: Product and vendor ratings

### 3. API Endpoints

**Vendors**
- POST /api/v1/vendors - Register vendor
- GET /api/v1/vendors/{id} - Get vendor profile
- PUT /api/v1/vendors/{id} - Update vendor
- GET /api/v1/vendors/{id}/products - List vendor products

**Products**
- POST /api/v1/products - Create product
- GET /api/v1/products - List/search products
- GET /api/v1/products/{id} - Get product details
- PUT /api/v1/products/{id} - Update product
- DELETE /api/v1/products/{id} - Delete product

**Orders**
- POST /api/v1/orders - Create order
- GET /api/v1/orders - List orders
- GET /api/v1/orders/{id} - Get order details
- PUT /api/v1/orders/{id}/status - Update order status

**Reviews**
- POST /api/v1/reviews - Create review
- GET /api/v1/products/{id}/reviews - Get product reviews
- GET /api/v1/vendors/{id}/reviews - Get vendor reviews

**Product Staging**
- POST /api/v1/bookmarks - Bookmark product for staging
- GET /api/v1/bookmarks - Get user's bookmarked products
- DELETE /api/v1/bookmarks/{id} - Remove bookmark
- POST /api/v1/staging - Stage product in design
- GET /api/v1/staging/design/{design_id} - Get staged products for design
- GET /api/v1/staging/design/{design_id}/procurement - Generate procurement list

## Data Models

### Vendor
- id, user_id, company_name, description
- email, phone, address
- verification_status, rating
- created_at, updated_at

### Product
- id, vendor_id, name, description
- category, price, inventory_quantity
- images, specifications
- **staging_data**: 3D model URL, dimensions (length/width/height), material properties
- **model_format**: GLB/GLTF file reference
- is_active, created_at, updated_at

### ProductBookmark
- id, user_id, product_id
- notes, created_at

### DesignStaging
- id, design_id (from Design Service), product_id
- position, rotation, scale
- quantity, created_at

### Order
- id, customer_id, total_amount
- status, shipping_address
- created_at, updated_at

### OrderItem
- id, order_id, product_id
- quantity, unit_price, subtotal

### Review
- id, user_id, product_id, vendor_id
- rating, comment, verified_purchase
- created_at

## Technology Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: TiDB (MySQL-compatible)
- **Migrations**: Alembic
- **Authentication**: JWT (from User Service)
- **Testing**: Pytest
- **Caching**: Redis (optional)
