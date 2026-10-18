"""Recipient proposals and direct-authority decisions."""

from alembic import op

revision = "0020"
down_revision = "0019"


def upgrade():
    op.execute("ALTER TABLE ritual_assignments ADD COLUMN paused_by_id uuid REFERENCES users(id)")
    op.execute("""
CREATE TABLE change_requests (
	id UUID NOT NULL,
	kind VARCHAR(20) NOT NULL,
	requester_id UUID NOT NULL,
	approver_id UUID NOT NULL,
	relation_id UUID NOT NULL,
	relation_version_id UUID NOT NULL,
	ritual_assignment_id UUID,
	rule_assignment_id UUID,
	occurrence_id UUID,
	target_revision INTEGER,
	assignment_revision INTEGER,
	rule_revision INTEGER,
	rule_version_id UUID,
	result_assignment_id UUID,
	idempotency_key UUID NOT NULL,
	request_hash BYTEA NOT NULL,
	status VARCHAR(20) NOT NULL,
	revision INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE,
	decision_actor_id UUID,
	key_id VARCHAR(100) NOT NULL,
	nonce BYTEA NOT NULL,
	ciphertext BYTEA NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (requester_id, idempotency_key),
	CHECK (kind IN ('ritual_skip','ritual_pause','rule_add','rule_edit','rule_delete')),
	CHECK (status IN ('pending','approved','rejected','withdrawn')),
	CHECK ((kind='rule_add'
 AND ritual_assignment_id IS NULL
 AND rule_assignment_id IS NULL
 AND occurrence_id IS NULL)
 OR (kind IN ('rule_edit','rule_delete')
 AND rule_assignment_id IS NOT NULL
 AND ritual_assignment_id IS NULL
 AND occurrence_id IS NULL)
 OR (kind='ritual_pause'
 AND ritual_assignment_id IS NOT NULL
 AND rule_assignment_id IS NULL
 AND occurrence_id IS NULL)
 OR (kind='ritual_skip'
 AND ritual_assignment_id IS NOT NULL
 AND occurrence_id IS NOT NULL
 AND rule_assignment_id IS NULL)),
	FOREIGN KEY(requester_id) REFERENCES users (id),
	FOREIGN KEY(approver_id) REFERENCES users (id),
	FOREIGN KEY(relation_id) REFERENCES authority_relations (id),
	FOREIGN KEY(relation_version_id) REFERENCES relation_versions (id),
	FOREIGN KEY(ritual_assignment_id) REFERENCES ritual_assignments (id),
	FOREIGN KEY(rule_assignment_id) REFERENCES rule_assignments (id),
	FOREIGN KEY(occurrence_id) REFERENCES ritual_occurrences (id),
	FOREIGN KEY(rule_version_id) REFERENCES rule_versions (id),
	FOREIGN KEY(result_assignment_id) REFERENCES rule_assignments (id),
	FOREIGN KEY(decision_actor_id) REFERENCES users (id)
)

;
CREATE UNIQUE INDEX pending_ritual_pause ON change_requests (ritual_assignment_id)
 WHERE status='pending'
 AND kind='ritual_pause';
CREATE UNIQUE INDEX pending_rule_request ON change_requests (rule_assignment_id)
 WHERE status='pending'
 AND rule_assignment_id IS NOT NULL;
CREATE UNIQUE INDEX pending_ritual_request ON change_requests
 (ritual_assignment_id, kind, occurrence_id)
 WHERE status='pending'
 AND kind='ritual_skip'""")


def downgrade():
    op.execute("DROP TABLE change_requests")
    op.execute("ALTER TABLE ritual_assignments DROP COLUMN paused_by_id")
