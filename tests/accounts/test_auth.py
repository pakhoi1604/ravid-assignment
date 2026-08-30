import jwt
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_token_obtain_and_refresh(client):
    user_model = get_user_model()
    user_model.objects.create_user(username="ada", password="correct-password")

    token_response = client.post(
        reverse("token_obtain_pair"),
        {"username": "ada", "password": "correct-password"},
        content_type="application/json",
    )

    assert token_response.status_code == 200
    token_payload = token_response.json()
    assert token_payload["access"]
    assert token_payload["refresh"]
    access_payload = jwt.decode(
        token_payload["access"],
        options={"verify_signature": False},
        algorithms=["HS256"],
    )
    assert access_payload["exp"] - access_payload["iat"] == 7 * 24 * 60 * 60

    refresh_response = client.post(
        reverse("token_refresh"),
        {"refresh": token_payload["refresh"]},
        content_type="application/json",
    )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access"]


@pytest.mark.django_db
def test_token_obtain_rejects_invalid_credentials(client):
    response = client.post(
        reverse("token_obtain_pair"),
        {"username": "missing", "password": "wrong"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_jwt_lifetimes_are_reviewer_friendly():
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].days == 7
    assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days == 30


def test_document_upload_requires_authentication(client):
    response = client.post(reverse("document-upload"))

    assert response.status_code == 401
