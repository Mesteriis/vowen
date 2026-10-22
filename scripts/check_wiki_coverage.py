"""Audit every reference fixture; a nonzero exit means the full Wiki goal is unfinished."""

import json
import re
from collections import Counter

from vowen.modules.references.fixtures import CATALOGUES, fixture_rows
from vowen.modules.wiki.catalogue_articles import (
    CatalogueArticle,
    load_catalogue_articles,
)
from vowen.modules.wiki.device_articles import DeviceArticle
from vowen.modules.wiki.device_review import load_reviewed_device_articles
from vowen.modules.wiki.pose_articles import PoseArticle
from vowen.modules.wiki.pose_review import load_reviewed_pose_articles
from vowen.modules.wiki.practice_articles import PracticeArticle
from vowen.modules.wiki.practice_review import load_reviewed_practice_articles


def report() -> dict[str, object]:
    extra = {(a.reference.kind, a.reference.uid): a for a in load_catalogue_articles()}
    domain: dict[str, dict[str, DeviceArticle | PoseArticle | PracticeArticle]] = {
        "practices": {a.code: a for a in load_reviewed_practice_articles()},
        "devices": {a.code: a for a in load_reviewed_device_articles()},
        "poses": {a.code: a for a in load_reviewed_pose_articles()},
    }
    entries = []
    for kind in CATALOGUES:
        for row in fixture_rows(kind):
            article: CatalogueArticle | DeviceArticle | PoseArticle | PracticeArticle | None
            article = extra.get((kind, row["uid"]))
            if article is None:
                article = domain.get(kind, {}).get(row["extra"]["code"])
            gaps = []
            # Repeating the label is not an explanation, even when the field is nonempty.
            label = re.sub(r"[\W_]+", "", row["name"].casefold())
            description = re.sub(r"[\W_]+", "", row["description"].casefold())
            if not description or description == label:
                gaps.append("reference_description")
            if article is None:
                gaps.extend(["wiki_article", "sources", "curated_links"])
            else:
                if not article.body.strip():
                    gaps.append("wiki_article")
                if not article.sources:
                    gaps.append("sources")
                if (kind, row["uid"]) not in extra and not re.search(
                    r"\]\(#wiki\?page=[0-9a-f-]{36}\)", article.body, re.IGNORECASE,
                ):
                    gaps.append("curated_links")
            entries.append({
                "kind": kind, "uid": str(row["uid"]), "name": row["name"], "gaps": gaps,
            })
    counts = Counter(gap for entry in entries for gap in entry["gaps"])
    return {
        "scope": "all current reference fixtures",
        "catalogues": len(CATALOGUES), "entries": len(entries),
        "articles_present": sum("wiki_article" not in e["gaps"] for e in entries),
        "gaps": dict(counts), "structural_complete": not counts,
        "limitation": "Fixture audit only; sources present are not proof of factual review or live links.",
        "items": entries,
    }


if __name__ == "__main__":
    result = report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["structural_complete"] else 1)
