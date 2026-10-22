from vowen.core.config import Settings
from vowen.main import create_app


def test_wiki_contract_contains_limits_and_separate_public_admin_routes():
    schema = create_app(Settings()).openapi()
    paths = schema["paths"]
    assert set(paths["/api/v1/wiki/pages/{uid}"]) == {"get"}
    assert "post" in paths["/api/v1/wiki/admin/pages/{uid}/publish"]
    assert "post" in paths["/api/v1/wiki/admin/seed-references"]
    doc = schema["components"]["schemas"]["WikiDocument"]["properties"]
    assert doc["title"]["maxLength"] == 160
    assert doc["body"]["maxLength"] == 100000
    assert doc["sources"]["maxItems"] == 20


def test_reference_link_contract_is_typed_and_exposes_only_reader_identifiers():
    schema = create_app(Settings()).openapi()
    operation = schema["paths"]["/api/v1/wiki/reference-links/{kind}"]["get"]
    kind = next(p for p in operation["parameters"] if p["name"] == "kind")
    assert len(kind["schema"]["enum"]) == 17
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["type"] == "array"
    link = schema["components"]["schemas"]["WikiReferenceLink"]
    assert set(link["properties"]) == {"reference_uid", "page_uid"}
    assert all(p["format"] == "uuid" for p in link["properties"].values())
