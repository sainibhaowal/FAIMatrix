import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from faim.config.database import Base


def _gen_uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.datetime.utcnow()


# =============================================================================
# Core Models - Simplified: User → Graph (Direct)
# =============================================================================


class User(Base):
    """User account. Each user owns their own graphs directly."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_sub = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Argon2 hash
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    status = Column(String, default="active")  # active, suspended, pending_verification

    # Email verification
    email_verification_token = Column(String, nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False)

    # Billing (optional, for future use)
    stripe_customer_id = Column(String, nullable=True)
    plan = Column(String, default="free")  # free, starter, pro

    # Avatar selection (stores avatar ID like "avatar_01", "avatar_02", etc.)
    avatar_id = Column(String, nullable=True, default="avatar_01")

    # Usage Tracking (for billing)
    memories_count = Column(BigInteger, default=0)  # Number of memories stored
    memories_max = Column(BigInteger, default=1000)  # Plan limit (free=1k, starter=10k, pro=100k)
    storage_used_bytes = Column(BigInteger, default=0)  # Storage used in bytes
    storage_max_bytes = Column(BigInteger, default=104_857_600)  # 100MB for free
    api_calls_count = Column(BigInteger, default=0)  # API calls this month
    api_calls_max = Column(BigInteger, default=10000)  # Plan limit
    api_calls_reset_at = Column(DateTime, nullable=True)  # Monthly reset date
    last_usage_update = Column(DateTime, nullable=True)  # Last time usage was updated

    # Relationships
    graphs = relationship("GraphOwnership", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    documents = relationship("Document", back_populates="user")


class GraphOwnership(Base):
    """User's knowledge graph. Direct ownership by User (no Org/Project layer)."""

    __tablename__ = "graphs"

    graph_id = Column(String, primary_key=True)  # FAIM graph ID (e.g., U:abc123)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=True)  # User-friendly name
    created_at = Column(DateTime, default=_utcnow)
    last_accessed_at = Column(DateTime, default=_utcnow)
    status = Column(String, default="active")

    user = relationship("User", back_populates="graphs")


class Document(Base):
    """Uploaded documents. Direct ownership by User."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    graph_id = Column(String, nullable=True)  # Optional: specific graph
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="documents")


class APIKey(Base):
    """API keys. Direct ownership by User."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=False, index=True)  # e.g., "sk_live_..."
    key_hash = Column(String, nullable=False)  # Argon2 hash
    scopes = Column(JSONB, default=list)  # ["read", "write"]
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, revoked

    user = relationship("User", back_populates="api_keys")


# =============================================================================
# Usage & Audit Models
# =============================================================================


class AuditLog(Base):
    """Audit log for security events."""

    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)  # create, read, update, delete
    target_type = Column(String, nullable=True)  # graph, node, user
    target_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    outcome = Column(String, default="success")


class FeatureFlag(Base):
    """Feature flags for gradual rollouts."""

    __tablename__ = "feature_flags"

    name = Column(String, primary_key=True)
    is_enabled = Column(Boolean, default=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_utcnow)


class UsageEvent(Base):
    """Tracks API calls for billing and metrics."""

    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    graph_id = Column(String, nullable=True, index=True)

    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)

    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)

    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    __table_args__ = (Index("ix_usage_events_user_ts", "user_id", "ts"),)


# =============================================================================
# FAIM Core Storage Models
# =============================================================================


class NodeStorage(Base):
    """FAIM Node storage - the fractal memory graph nodes."""

    __tablename__ = "faim_nodes"

    node_id = Column(String, primary_key=True)
    graph_id = Column(String, ForeignKey("graphs.graph_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    vec = Column(LargeBinary, nullable=False)  # Serialized numpy float32 array
    parents = Column(JSONB, default=list)
    children = Column(JSONB, default=list)
    payload_ref = Column(String, nullable=True)  # SHA256 reference to PayloadStorage

    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_faim_nodes_user_graph", "user_id", "graph_id"),)


class PayloadStorage(Base):
    """FAIM Payload storage - actual text content for nodes."""

    __tablename__ = "faim_payloads"

    payload_ref = Column(String, primary_key=True)  # SHA256 hash
    graph_id = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    content = Column(Text, nullable=False)
    encrypted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_faim_payloads_user_graph", "user_id", "graph_id"),)


class EventJournalEntry(Base):
    """FAIM Event Journal - audit log for graph operations."""

    __tablename__ = "faim_journal"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime, default=_utcnow, index=True)

    graph_id = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    kind = Column(String, nullable=False)  # create, update, delete, merge, prune, evolve
    node_id = Column(String, nullable=True)
    details = Column(JSONB, default=dict)

    __table_args__ = (Index("ix_faim_journal_user_ts", "user_id", "ts"),)


# =============================================================================
# OTP Authentication
# =============================================================================


class OTPCode(Base):
    """
    One-Time Password codes for passwordless authentication.

    Security:
    - OTP stored as SHA256 hash (never plaintext)
    - 5-minute expiration
    - Max 3 verification attempts
    - Marked as used after successful verification
    """

    __tablename__ = "otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)  # SHA256 hex digest
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    used_at = Column(DateTime, nullable=True)  # Set when OTP is successfully verified

    __table_args__ = (Index("ix_otp_email_expires", "email", "expires_at"),)


class RefreshToken(Base):
    """
    Refresh tokens for session management.

    Security:
    - Token stored as SHA256 hash
    - 7-day expiration
    - Can be revoked (for logout)
    """

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)  # SHA256 hex digest
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    revoked_at = Column(DateTime, nullable=True)  # Set when token is revoked (logout)

    user = relationship("User")
