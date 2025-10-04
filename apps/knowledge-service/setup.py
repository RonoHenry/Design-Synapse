"""Setup file for knowledge-service package."""
from setuptools import setup, find_packages

setup(
    name="knowledge-service",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "sqlalchemy",
        "uvicorn",
        "alembic",
        "pytest",
    ],
    python_requires=">=3.9",
)