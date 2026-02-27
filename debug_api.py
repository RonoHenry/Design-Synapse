import httpx
from fastapi.testclient import TestClient
from src.main import app
from src.models.booking import Booking, BookingStatus
from src.models.quote import Quote, QuoteStatus
from src.models.service_request import RequestStatus, ServiceRequest

from tests.conftest import TestingSessionLocal


def debug_test():
    client = TestClient(app)
    # The conftest fixtures should already be applied if we use the client from conftest
    # But here I'm just doing a quick check.

    # Let's see what's in the DB
    session = TestingSessionLocal()
    booking = session.query(Booking).first()
    if booking:
        print(
            f"Booking ID: {booking.id}, Status: {booking.status}, Provider: {booking.provider_id}, Client: {booking.client_id}"
        )

        # Test start
        response = client.post(f"/api/v1/bookings/{booking.id}/start")
        print(f"Start Response: {response.status_code}, Body: {response.json()}")

    session.close()


if __name__ == "__main__":
    # This won't work easily because of the conftest setup (db_session fixture)
    # I'll just run pytest with -s
    pass
