from vowen.core.config import Settings
from vowen.main import create_app


def test_participant_profile_contract_keeps_participant_lists_minimal():
    document = create_app(Settings()).openapi()
    paths = document["paths"]
    assert set(paths["/api/v1/me/profile/draft"]) >= {"get", "put", "delete"}
    assert "post" in paths["/api/v1/me/profile/publish"]
    schemas = document["components"]["schemas"]
    assert schemas["ProfileDraftPatch"]["properties"]["expected_version"]["minimum"] == 0
    assert set(schemas["ParticipantView"]["properties"]) == {"id", "display_name", "profile_labels"}
    assert schemas["PracticeChoice"]["properties"]["attitude"]["enum"] == [
        "not_specified",
        "like",
        "want_to_try",
        "conditional",
        "taboo",
    ]
