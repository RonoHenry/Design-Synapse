"""
Script to create default roles in the database.

This module provides functionality to initialize the default roles required by
the application. It ensures that basic roles like 'user' are present in the
database before the application starts.
"""

from sqlalchemy import text
from ..infrastructure.database import engine


def create_default_roles():
    """Create default roles in the database.

    This function creates the default 'user' role if it doesn't already exist.
    The role is inserted with a description and uses ON CONFLICT DO NOTHING
    to handle cases where the role already exists.
    """
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": "user", "description": "Regular user"},
        )
        conn.commit()


if __name__ == "__main__":
    create_default_roles()
