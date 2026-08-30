from django.urls import reverse


def test_health_endpoint_is_public(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_public(client):
    response = client.get(reverse("schema"))

    assert response.status_code == 200
    assert "application/vnd.oai.openapi" in response["Content-Type"]
    assert "/api/chat/query/" in response.data["paths"]
    assert "post" in response.data["paths"]["/api/chat/query/"]
    responses = response.data["paths"]["/api/chat/query/"]["post"]["responses"]
    assert {"200", "400", "401", "403", "429", "503"} <= set(responses)


def test_swagger_ui_is_public(client):
    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200
