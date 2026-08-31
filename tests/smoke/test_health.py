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

    schemas = response.data["components"]["schemas"]
    request_schema = schemas["ChatQuery"]
    assert request_schema["properties"]["use_hyde"] == {
        "type": "boolean",
        "default": False,
    }
    assert request_schema["required"] == ["query"]

    answer_schema = schemas["ChatAnswer"]
    assert set(answer_schema["properties"]) == {"answer", "retrieval_metadata"}
    assert answer_schema["properties"]["retrieval_metadata"]["$ref"].endswith("/RetrievalMetadata")

    metadata_schema = schemas["RetrievalMetadata"]
    assert set(metadata_schema["properties"]) == {
        "mode",
        "hypothetical_passage",
        "fallback_reason",
        "retrieved_chunks_count",
        "retrieved_chunks",
    }
    assert set(metadata_schema["required"]) == set(metadata_schema["properties"])
    assert schemas["ModeEnum"]["enum"] == ["standard", "hyde"]
    assert schemas["FallbackReasonEnum"]["enum"] == ["hyde_unavailable"]
    assert metadata_schema["properties"]["hypothetical_passage"]["nullable"] is True
    assert metadata_schema["properties"]["fallback_reason"]["nullable"] is True


def test_swagger_ui_is_public(client):
    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200
