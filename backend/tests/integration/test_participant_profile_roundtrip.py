from uuid import uuid4

from test_participant_profile_draft import setup_profile


async def test_normalized_selections_roundtrip_and_discard_versions(api):
    from vowen.modules.references.models import (
        Allergen,
        BiologicalSex,
        BodyPart,
        Device,
        Gender,
        Practice,
    )

    c, app, _, h = await setup_profile(api)
    ids = {
        kind: str(uuid4()) for kind in ("sex", "gender", "practice", "device", "body", "allergen")
    }
    async with app.state.sessions.begin() as db:
        for kind, model in [
            ("sex", BiologicalSex),
            ("gender", Gender),
            ("practice", Practice),
            ("device", Device),
            ("body", BodyPart),
            ("allergen", Allergen),
        ]:
            db.add(model(uid=ids[kind], name="Synthetic " + kind))
    version = 0
    sections = {
        "identity": {
            "biological_sex_uid": ids["sex"],
            "gender_uid": ids["gender"],
            "bio": "Private identity",
        },
        "dynamics": {
            "sex_preference": {"mode": "selected", "uids": [ids["sex"]]},
            "gender_preference": {"mode": "any", "uids": []},
        },
        "preferences": {
            "practices": [
                {
                    "practice_uid": ids["practice"],
                    "attitude": "want_to_try",
                    "experience": "experienced",
                    "participation": "receive",
                    "conditions": "A condition",
                }
            ],
            "devices": [
                {"uid": ids["device"], "attitude": "conditional", "conditions": "Device condition"}
            ],
            "body_parts": [{"uid": ids["body"], "attitude": "taboo"}],
        },
        "health": {"allergen_uids": [ids["allergen"]], "care_practice_uids": [ids["practice"]]},
    }
    for section, value in sections.items():
        response = await c.put(
            "/api/v1/me/profile/draft",
            headers=h,
            json={"expected_version": version, "section": section, "value": value, "step": 3},
        )
        assert response.status_code == 200, response.text
        version = response.json()["version"]
    published = await c.post(
        "/api/v1/me/profile/publish", headers=h, json={"expected_draft_version": version}
    )
    assert published.status_code == 200, published.text
    doc = (await c.get("/api/v1/me/profile", headers=h)).json()["document"]
    assert doc["preferences"]["practices"][0]["experience"] == "experienced"
    assert doc["preferences"]["practices"][0]["attitude"] == "want_to_try"
    assert doc["preferences"]["devices"][0]["conditions"] == "Device condition"
    assert doc["identity"]["gender_uid"] == ids["gender"]
    assert doc["dynamics"]["sex_preference"] == {"mode": "selected", "uids": [ids["sex"]]}
    assert doc["health"]["allergen_uids"] == [ids["allergen"]]
    draft = (
        await c.put("/api/v1/me/profile/draft", headers=h, json={"expected_version": 0, "step": 1})
    ).json()
    assert (
        await c.delete(
            "/api/v1/me/profile/draft", headers=h, params={"expected_version": draft["version"]}
        )
    ).status_code == 204
    fresh = (
        await c.put("/api/v1/me/profile/draft", headers=h, json={"expected_version": 0, "step": 2})
    ).json()
    assert fresh["version"] > draft["version"]
    assert (
        await c.delete(
            "/api/v1/me/profile/draft", headers=h, params={"expected_version": draft["version"]}
        )
    ).status_code == 409
