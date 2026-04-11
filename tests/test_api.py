from unittest.mock import Mock

import pytest
import requests

from seqtypo import api, models


class DummyResponse:
    def __init__(self, payload=None, text="", status_code=200, reason="OK", raise_http=False):
        self._payload = payload or {}
        self.text = text
        self.status_code = status_code
        self.reason = reason
        self._raise_http = raise_http

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self._raise_http:
            raise requests.HTTPError("boom")


class FakeResource:
    def __init__(self, databases):
        self.databases = databases


def test_rest_client_do_request_merges_headers(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse(payload={"ok": True})

    monkeypatch.setattr(api.requests, "request", fake_request)

    client = api.RestClient(ssl_verify=False)
    client.set_headers({"Authorization": "Bearer token"})

    response = client.get("https://example.org", headers={"X-Test": "1"})

    assert response.json() == {"ok": True}
    assert captured["verify"] is False
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["headers"]["X-Test"] == "1"


def test_rest_client_raises_api_service_error_on_http_error(monkeypatch):
    monkeypatch.setattr(
        api.requests,
        "request",
        lambda **kwargs: DummyResponse(status_code=400, reason="Bad Request", raise_http=True),
    )

    with pytest.raises(api.ApiServiceError, match="Error 400: Bad Request"):
        api.RestClient().get("https://example.org")


def test_big_sdb_get_databases_applies_filters(monkeypatch):
    fake_resources = [
        FakeResource(
            models.DatabaseList(
                [
                    models.DatabaseModel(
                        name="a_seqdef",
                        description="REST API access to Neisseria seqdef database",
                        href="https://example.org/a",
                    ),
                    models.DatabaseModel(
                        name="b_isolates",
                        description="REST API access to Salmonella isolates database",
                        href="https://example.org/b",
                    ),
                ]
            )
        )
    ]

    monkeypatch.setattr(api.BigSdbApi, "get_resources", lambda self: fake_resources)

    service = api.BigSdbApi("https://fake")
    filtered = service.get_databases(pattern="Neiss", exact_match=False)

    assert len(filtered) == 1
    assert filtered[0].subject == "Neisseria"


def test_api_model_service_from_url_builds_model(monkeypatch):
    fake_json = {
        "resources": [
            {
                "name": "PubMLST",
                "description": "Public datasets",
                "databases": [
                    {
                        "name": "x_seqdef",
                        "description": "REST API access to X seqdef database",
                        "href": "https://example.org/x",
                    }
                ],
            }
        ]
    }
    mock_get = Mock(return_value=DummyResponse(payload=fake_json))
    monkeypatch.setattr(api.RestClient, "get", mock_get)

    model_service = api.ResourceApi.from_url("https://example.org")

    assert isinstance(model_service.model, models.ApiResourceCollectionModel)
    mock_get.assert_called_once_with("https://example.org")


def test_sequence_query_handler_marks_base64(monkeypatch):
    posted = {}

    def fake_post(self, url, json=None, **kwargs):
        posted["url"] = url
        posted["json"] = json
        return DummyResponse(payload={"status": "ok"})

    monkeypatch.setattr(api.RestClient, "post", fake_post)

    handler = api.SequenceQueryHandler(query_endpoint="https://example.org/query")
    response = handler.query_sequence("QUNURw==")

    assert response == {"status": "ok"}
    assert posted["url"] == "https://example.org/query"
    assert posted["json"]["base64"] is True


def test_full_database_api_get_schemes(monkeypatch):
    full_db = models.FullDatabaseModel(
        schemes="https://example.org/schemes",
        loci="https://example.org/loci",
    )

    fake_payload = {
        "records": 1,
        "schemes": [
            {
                "scheme": "https://example.org/schemes/1",
                "description": "Simple MLST scheme",
            }
        ],
    }
    monkeypatch.setattr(api.RestClient, "get", lambda self, url: DummyResponse(payload=fake_payload))

    full_db_api = api.FullDatabaseApi(full_db)
    schemes = full_db_api.get_schemes()

    assert len(schemes) == 1
    assert schemes[0].query_endpoint.endswith("/sequence")


def test_scheme_collection_return_by_idx():
    collection = models.SchemeCollectionModel(
        records=2,
        schemes=[
            {"scheme": "https://example.org/schemes/10", "description": "MLST A"},
            {"scheme": "https://example.org/schemes/11", "description": "MLST B"},
        ],
    )

    service = api.SchemeCollectionApi(collection)

    result = service.return_scheme_by_idx(11)

    assert str(result.scheme).endswith("/11")
