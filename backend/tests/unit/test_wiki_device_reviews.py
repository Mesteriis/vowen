import json
import re
from importlib.resources import files
from uuid import uuid5

from vowen.modules.references.fixtures import fixture_rows
from vowen.modules.wiki.device_articles import load_device_articles
from vowen.modules.wiki.device_review import (
    load_device_reviews,
    load_reviewed_device_articles,
)
from vowen.modules.wiki.editorial import editorial_uid, load_editorial
from vowen.modules.wiki.seed import NAMESPACE


def test_reviewed_devices_preserve_originals_and_have_real_targets_and_source_scopes():
    originals = {a.code: a for a in load_device_articles()}
    reviews = {r.code: r for r in load_device_reviews()}
    enriched = {a.code: a for a in load_reviewed_device_articles()}
    root = files("vowen.modules.wiki").joinpath("fixtures", "ru", "device-reviews-v1")
    registry = json.loads(root.joinpath("source-review.json").read_text("utf-8"))
    sources = {s["url"]: s for s in registry["sources"]}
    targets = {str(uuid5(NAMESPACE, "devices:" + str(r["uid"])))
               for r in fixture_rows("devices")} | {
        str(editorial_uid("article:" + a.key)) for a in load_editorial().articles
    }
    assert len(originals) == len(enriched) == 62
    assert len(reviews) == 62
    for code, article in enriched.items():
        original = originals[code]
        if code not in reviews:
            assert article == original
            continue
        assert article.body.startswith(original.body.rstrip())
        assert article.summary == original.summary
        assert article.sources == reviews[code].sources
        links = set(re.findall(r"#wiki\?page=([0-9a-f-]{36})", article.body))
        assert len(links) == len(reviews[code].related_device_codes) + len(
            reviews[code].related_pages,
        )
        assert links <= targets
        for source in article.sources:
            assert sources[source.url]["publisher"] and sources[source.url]["scope"]
            assert sources[source.url]["checked_on"] == "2026-10-22"
            assert source.url in article.body
