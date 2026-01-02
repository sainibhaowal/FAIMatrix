import uuid
import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Integer,
    Index,
    LargeBinary,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from faim.db import Base


def _gen_uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_sub = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    status = Column(String, default="active")  # active, suspended

    # Relationships
    memberships = relationship("OrgMember", back_populates="user")
    owned_orgs = relationship("Org", back_populates="owner")


class Org(Base):
    __tablename__ = "orgs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    # Relationships
    owner = relationship("User", back_populates="owned_orgs")
    members = relationship("OrgMember", back_populates="org")
    projects = relationship("Project", back_populates="org")


class OrgMember(Base):
    __tablename__ = "org_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")  # owner, admin, member
    joined_at = Column(DateTime, default=_utcnow)

    org = relationship("Org", back_populates="members")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (Index("ix_org_members_user_org", "user_id", "org_id", unique=True),)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")  # free, pro, enterprise

    # Billing Info
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="active")  # active, past_due, canceled
    plan_limits = Column(JSONB, default=dict)  # {"graphs": 1, "storage_mb": 100}

    created_at = Column(DateTime, default=_utcnow)

    org = relationship("Org", back_populates="projects")
    graphs = relationship("GraphOwnership", back_populates="project")
    api_keys = relationship("APIKey", back_populates="project")
    documents = relationship("Document", back_populates="project")


class GraphOwnership(Base):
    __tablename__ = "graphs"

    graph_id = Column(String, primary_key=True)  # The actual FAIM graph ID (e.g., G:...)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=True)  # User-friendly name
    created_at = Column(DateTime, default=_utcnow)
    last_accessed_at = Column(DateTime, default=_utcnow)
    status = Column(String, default="active")

    project = relationship("Project", back_populates="graphs")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    graph_id = Column(String, nullable=True)  # Optional: if this doc feeds a specific graph
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="documents")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=False, index=True)  # e.g., "sk-..."
    key_hash = Column(String, nullable=False)  # Argon2 hash of the full key
    scopes = Column(JSONB, default=list)  # ["read", "write"]
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, revoked

    project = relationship("Project", back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    actor_key_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)

    action = Column(String, nullable=False)  # create, read, update, delete
    target_type = Column(String, nullable=True)  # graph, node, org
    target_id = Column(String, nullable=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    outcome = Column(String, default="success")


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    name = Column(String, primary_key=True)
    is_enabled = Column(Boolean, default=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_utcnow)


class UsageEvent(Base):
    """
    Tracks every API call for billing, metrics, and abuse detection.
    Supports both daily rollups and per-request auditing.
    """

    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow, index=True)

    # Tenant context
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    graph_id = Column(String, nullable=True, index=True)

    # Actor (either user via JWT or API key)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    actor_key_id = Column(UUID(as_uuid=True), nullable=True)

    # Request info
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)  # GET, POST, etc.

    # Usage metrics
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)

    # Response info
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    # Client info
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_usage_events_project_ts", "project_id", "ts"),
        Index("ix_usage_events_actor_ts", "actor_user_id", "ts"),
    )


# =============================================================================
# FAIM Core Storage Models - Production Postgres Backend
# =============================================================================


class NodeStorage(Base):
    """FAIM Node storage - stores the fractal memory graph nodes.

    Each node belongs to a graph, which belongs to a project.
    The vector is stored as a binary blob (serialized numpy array).
    """

    __tablename__ = "faim_nodes"

    # Primary key: node_id is the FAIM-generated unique ID
    node_id = Column(String, primary_key=True)

    # Multi-tenant isolation
    graph_id = Column(String, ForeignKey("graphs.graph_id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Node data
    vec = Column(LargeBinary, nullable=False)  # Serialized numpy float32 array
    parents = Column(JSONB, default=list)  # [{parent_id, fraction}, ...]
    children = Column(JSONB, default=list)  # [child_id, ...]
    payload_ref = Column(String, nullable=True)  # SHA256 reference to PayloadStorage

    # Usage tracking for evolution/pruning
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_faim_nodes_project_graph", "project_id", "graph_id"),)


class PayloadStorage(Base):
    """FAIM Payload storage - stores the actual text content for nodes.

    Payloads are referenced by SHA256 hash for deduplication.
    Content can optionally be encrypted at rest.
    """

    __tablename__ = "faim_payloads"

    # Primary key: SHA256 hash of the content
    payload_ref = Column(String, primary_key=True)

    # Multi-tenant isolation
    graph_id = Column(String, nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Content
    content = Column(Text, nullable=False)  # The actual text content
    encrypted = Column(Boolean, default=False)  # True if content is Fernet-encrypted

    # Metadata
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_faim_payloads_project_graph", "project_id", "graph_id"),)


class EventJournalEntry(Base):
    """FAIM Event Journal - audit log for all graph operations.

    Records creates, updates, deletes, merges, prunes for the evolution system.
    """

    __tablename__ = "faim_journal"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow, index=True)

    # Multi-tenant context
    graph_id = Column(String, nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    # Event info
    kind = Column(String, nullable=False)  # create, update, delete, merge, prune, evolve
    node_id = Column(String, nullable=True)
    details = Column(JSONB, default=dict)  # Additional event-specific data

    __table_args__ = (Index("ix_faim_journal_project_ts", "project_id", "ts"),)
