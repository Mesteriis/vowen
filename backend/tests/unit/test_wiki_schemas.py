from importlib.util import find_spec
from uuid import uuid4

import pytest
from pydantic import ValidationError


def schemas():
    assert find_spec("vowen.modules.wiki") is not None, "Wiki module is missing"
    from vowen.modules.wiki import schemas

    return schemas


def document(**changes):
    return dict(section_uid=uuid4(), title="Article", summary="", body="Text", **changes)


def test_reference_card_requires_exactly_one_main_reference():
    s = schemas()
    s.WikiPageCreate(kind="article", document=document())
    s.WikiPageCreate(kind="encyclopedia", practice_uid=uuid4(), document=document())
    for fields in [{}, {"practice_uid": uuid4(), "pose_uid": uuid4()}]:
        with pytest.raises(ValidationError):
            s.WikiPageCreate(kind="encyclopedia", document=document(), **fields)
    with pytest.raises(ValidationError):
        s.WikiPageCreate(kind="article", device_uid=uuid4(), document=document())


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "x" * 161),
        ("summary", "x" * 601),
        ("body", "x" * 100001),
        ("practice_uids", [uuid4() for _ in range(51)]),
        ("sources", [{"url": "https://example.org"}] * 21),
        ("thumbnail", "https://example.org/a.png"),
        ("thumbnail", "/does-not-exist.png"),
        ("sources", [{"url": "https://user:password@example.org"}]),
        ("sources", [{"url": "javascript:alert(1)"}]),
    ],
    ids=[
        "title",
        "summary",
        "body",
        "links",
        "sources",
        "remote-image",
        "missing-image",
        "credentials",
        "scheme",
    ],
)
def test_document_limits_and_safe_assets(field, value):
    s = schemas()
    fields = document()
    fields[field] = value
    with pytest.raises(ValidationError):
        s.WikiDocument(**fields)


@pytest.mark.parametrize("url", ["https://@example.org", "https://example.org:not-a-port"])
def test_source_rejects_empty_credentials_and_invalid_ports(url):
    with pytest.raises(ValidationError):
        schemas().WikiSource(url=url)


def test_installed_static_root_validates_files_and_rejects_escape(tmp_path, monkeypatch):
    root = tmp_path / "static"
    root.mkdir()
    (root / "thumbnail.png").write_bytes(b"fixture")
    outside = tmp_path / "private.png"
    outside.write_bytes(b"private fixture")
    (root / "escape.png").symlink_to(outside)
    monkeypatch.setenv("VOWEN_STATIC_ROOT", str(root))
    model = schemas().WikiDocument
    assert model(**document(thumbnail="/thumbnail.png")).thumbnail == "/thumbnail.png"
    for path in ("/../private.png", "/escape.png", "/missing.png"):
        with pytest.raises(ValidationError):
            model(**document(thumbnail=path))
