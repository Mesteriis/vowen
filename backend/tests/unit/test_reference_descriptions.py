import re
from collections import Counter

from vowen.modules.references.description_refresh import description_updates
from vowen.modules.references.fixtures import CATALOGUES, fixture_rows


def test_every_reference_has_explanatory_description_and_only_original_gaps_are_replaced():
    updates = description_updates()
    assert Counter(kind for kind, _, _ in updates) == {
        "practices": 79, "devices": 24, "body-parts": 23, "practice-categories": 12,
    }
    def normalize(text):
        return re.sub(r"[\W_]+", "", text.casefold())

    for _, baseline, description in updates:
        assert normalize(baseline["name"]) == normalize(baseline["description"])
        assert normalize(description) != normalize(baseline["name"])
        assert 40 <= len(description) <= 600
    for kind in CATALOGUES:
        for row in fixture_rows(kind):
            assert normalize(row["description"]) != normalize(row["name"])
