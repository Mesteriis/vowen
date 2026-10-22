from datetime import UTC, datetime
from uuid import uuid4

from test_wiki_admin import ROOT, doc
from test_wiki_device_articles import setup

from vowen.modules.references.fixtures import CATALOGUES, fixture_rows
from vowen.modules.references.models import Practice
from vowen.modules.wiki.catalogue_articles import catalogue_page_uid, seed_catalogue_articles
from vowen.modules.wiki.editorial import seed_editorial_pages
from vowen.modules.wiki.models import WikiPage

LINKS = "/api/v1/wiki/reference-links/"


async def test_member_gets_exact_published_mapping_for_all_seventeen_catalogues(api):
    client, app, admin, member, actor, _ = await setup(api)
    async with app.state.sessions.begin() as db:
        await seed_editorial_pages(db, actor)
        await seed_catalogue_articles(db, actor)
    total = 0
    for kind in CATALOGUES:
        response = await client.get(LINKS + kind, headers=member)
        assert response.status_code == 200
        expected = {str(r["uid"]): str(catalogue_page_uid(kind, r["uid"]))
                    for r in fixture_rows(kind)}
        rows = response.json()
        assert all(set(row) == {"reference_uid", "page_uid"} for row in rows)
        assert {r["reference_uid"]: r["page_uid"] for r in rows} == expected
        assert (await client.get(LINKS + kind, headers=admin)).json() == rows
        total += len(rows)
    assert total == 438
    assert (await client.get(LINKS + "devices")).status_code == 401
    assert (await client.get(LINKS + "unknown", headers=member)).status_code == 422


async def test_reference_links_hide_archives_and_draft_only_pages_in_both_mapping_paths(api):
    client, app, _, member, actor, _ = await setup(api)
    async with app.state.sessions.begin() as db:
        await seed_editorial_pages(db, actor)
        await seed_catalogue_articles(db, actor)
        for kind, archive in (("practices", True), ("poses", False),
                              ("biological-sex", True), ("genders", False)):
            row = fixture_rows(kind)[0]
            page = await db.get(WikiPage, catalogue_page_uid(kind, row["uid"]))
            if archive:
                page.archived_at = datetime.now(UTC)
            else:
                page.published_revision_uid = None
    for kind in ("practices", "poses", "biological-sex", "genders"):
        response = await client.get(LINKS + kind, headers=member)
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == len(fixture_rows(kind)) - 1
        assert str(fixture_rows(kind)[0]["uid"]) not in {r["reference_uid"] for r in rows}


async def test_custom_encyclopedia_is_resolved_by_reference_not_canonical_fixture_uuid(api):
    client, app, admin, member, _, section = await setup(api, stubs=False)
    reference = uuid4()
    async with app.state.sessions.begin() as db:
        db.add(Practice(uid=reference, name="Авторская практика", description="Моё описание"))
    assert (await client.get(LINKS + "practices", headers=member)).json() == []
    response = await client.post(ROOT + "/pages", headers=admin, json={
        "kind": "encyclopedia", "practice_uid": str(reference),
        "document": doc(section, "Авторская статья"),
    })
    assert response.status_code == 200
    page = response.json()
    assert page["uid"] != str(catalogue_page_uid("practices", reference))
    assert (await client.get(LINKS + "practices", headers=member)).json() == []
    response = await client.post(ROOT + f'/pages/{page["uid"]}/publish', headers=admin, json={
        "expected_version": page["version"], "revision_uid": page["draft_revision_uid"],
    })
    assert response.status_code == 200
    expected = [{"reference_uid": str(reference), "page_uid": page["uid"]}]
    assert (await client.get(LINKS + "practices", headers=member)).json() == expected
    # A new draft must neither hide the existing publication nor leak draft metadata.
    page = response.json()
    response = await client.patch(ROOT + f'/pages/{page["uid"]}', headers=admin, json={
        "expected_version": page["version"], "document": doc(section, "Скрытый черновик"),
    })
    assert response.status_code == 200
    assert (await client.get(LINKS + "practices", headers=member)).json() == expected
    assert (await client.get(LINKS + "devices", headers=member)).json() == []
