"""Debug script to print registered routes."""

from src.main import app

print("Registered routes:")
for route in app.routes:
    print(f"{route.path} [{route.methods}]")