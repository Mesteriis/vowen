"""Shared Wiki tree and separately published immutable page revisions."""

from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0051"
down_revision = "0050"


def upgrade() -> None:
    op.create_table(
        "wiki_tree_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "wiki_sections",
        sa.Column("uid", sa.UUID(), primary_key=True),
        sa.Column("parent_uid", sa.UUID(), sa.ForeignKey("wiki_sections.uid", ondelete="RESTRICT")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("parent_uid IS NULL OR parent_uid <> uid"),
    )
    op.create_index("ix_wiki_sections_parent_uid", "wiki_sections", ["parent_uid"])
    op.create_table(
        "wiki_pages",
        sa.Column("uid", sa.UUID(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "practice_uid",
            sa.UUID(),
            sa.ForeignKey("reference_practices.uid", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "pose_uid",
            sa.UUID(),
            sa.ForeignKey("reference_poses.uid", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "device_uid",
            sa.UUID(),
            sa.ForeignKey("reference_devices.uid", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("draft_revision_uid", sa.UUID()),
        sa.Column("published_revision_uid", sa.UUID()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(kind='article' AND num_nonnulls(practice_uid,pose_uid,device_uid)=0) "
            "OR (kind='encyclopedia' AND "
            "num_nonnulls(practice_uid,pose_uid,device_uid)=1)",
            name="wiki_main_ref",
        ),
    )
    op.create_table(
        "wiki_revisions",
        sa.Column("uid", sa.UUID(), primary_key=True),
        sa.Column("page_uid", sa.UUID(), sa.ForeignKey("wiki_pages.uid"), nullable=False),
        sa.Column(
            "section_uid",
            sa.UUID(),
            sa.ForeignKey("wiki_sections.uid", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("thumbnail", sa.Text()),
        sa.Column("sources", JSONB(), nullable=False),
        sa.Column(
            "author_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("page_uid", "uid", name="wiki_revision_owner"),
    )
    for field, name in [
        ("draft_revision_uid", "wiki_draft_owner"),
        ("published_revision_uid", "wiki_publication_owner"),
    ]:
        op.create_foreign_key(
            name, "wiki_pages", "wiki_revisions", ["uid", field], ["page_uid", "uid"]
        )
    for field in ["page_uid", "section_uid"]:
        op.create_index("ix_wiki_revisions_" + field, "wiki_revisions", [field])
    for kind, ref in [("practices", "practice"), ("poses", "pose"), ("devices", "device")]:
        op.create_table(
            "wiki_revision_" + kind,
            sa.Column(
                "revision_uid", sa.UUID(), sa.ForeignKey("wiki_revisions.uid"), primary_key=True
            ),
            sa.Column(
                ref + "_uid",
                sa.UUID(),
                sa.ForeignKey("reference_" + kind + ".uid", ondelete="RESTRICT"),
                primary_key=True,
            ),
        )
    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO wiki_tree_state VALUES (1,1)"))
    for order, (key, title) in enumerate(
        [
            ("practices", "Практики"),
            ("poses", "Позы"),
            ("devices", "Девайсы"),
            ("articles", "Статьи"),
        ]
    ):
        conn.execute(
            sa.text(
                "INSERT INTO wiki_sections (uid,title,description,sort_order,version) "
                "VALUES (:uid,:title,'',:ord,1)"
            ),
            {
                "uid": uuid5(UUID("a4542385-e05b-4ea1-864b-6ad90b4e8375"), key),
                "title": title,
                "ord": order,
            },
        )


def downgrade() -> None:
    for name in ["wiki_draft_owner", "wiki_publication_owner"]:
        op.drop_constraint(name, "wiki_pages", type_="foreignkey")
    for name in [
        "wiki_revision_devices",
        "wiki_revision_poses",
        "wiki_revision_practices",
        "wiki_revisions",
        "wiki_pages",
        "wiki_sections",
        "wiki_tree_state",
    ]:
        op.drop_table(name)
