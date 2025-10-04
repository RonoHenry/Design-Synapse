from sqlalchemy import text
from ..infrastructure.database import engine


def create_default_roles():
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO roles (name, description) VALUES (:name, :description) ON CONFLICT (name) DO NOTHING"
            ),
            {"name": "user", "description": "Regular user"},
        )
        conn.commit()


if __name__ == "__main__":
    create_default_roles()
