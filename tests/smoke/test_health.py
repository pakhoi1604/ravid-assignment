from django.urls import reverse


def test_health_endpoint_is_public(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_public(client):
    response = client.get(reverse("schema"))

    assert response.status_code == 200
    assert "application/vnd.oai.openapi" in response["Content-Type"]


def test_swagger_ui_is_public(client):
    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200
