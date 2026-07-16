from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship

from core.database import Base

# ── Lookup Tables (standardised dropdown values) ──


class LookupReligion(Base):
    __tablename__ = "lookup_religions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class LookupCaste(Base):
    __tablename__ = "lookup_castes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class LookupOccupation(Base):
    __tablename__ = "lookup_occupations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    category = Column(String(64), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class LookupEducation(Base):
    __tablename__ = "lookup_educations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class LookupLanguage(Base):
    __tablename__ = "lookup_languages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    __table_args__ = (Index("idx_lookup_languages_active", "is_active"),)


# ── Profile Sections ──


class ProfileSection(Base):
    __tablename__ = "profile_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    name_hi = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    completion_weight = Column(Float, default=1.0, nullable=False)
    visibility_rule = Column(JSONB, nullable=True)
    min_app_version = Column(String(16), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    fields = relationship(
        "ProfileFieldDefinition",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ProfileFieldDefinition.display_order",
    )


# ── Profile Field Definitions ──


class ProfileFieldDefinition(Base):
    __tablename__ = "profile_field_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(
        Integer, ForeignKey("profile_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key = Column(String(64), unique=True, nullable=False)
    label = Column(String(128), nullable=False)
    label_hi = Column(String(128), nullable=True)
    field_type = Column(String(32), nullable=False, default="text")
    is_required = Column(Boolean, default=False, nullable=False)
    is_searchable = Column(Boolean, default=False, nullable=False)
    is_editable = Column(Boolean, default=True, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    default_value = Column(Text, nullable=True)
    lookup_table = Column(String(64), nullable=True)
    options = Column(JSONB, nullable=True)
    validation_rules = Column(JSONB, nullable=True)
    placeholder = Column(String(256), nullable=True)
    help_text = Column(Text, nullable=True)
    unit = Column(String(32), nullable=True)
    category = Column(String(64), nullable=True)
    pii = Column(Boolean, default=False, nullable=False)
    encrypt_at_rest = Column(Boolean, default=False, nullable=False)
    default_visibility = Column(
        String(32), default="public", nullable=False
    )
    completion_weight = Column(Float, default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    section = relationship("ProfileSection", back_populates="fields")
    values = relationship(
        "ProfileFieldValue", back_populates="field_definition", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_pfd_section_order", "section_id", "display_order"),)


# ── Profile Field Values (with moderation) ──


class ProfileFieldValue(Base):
    __tablename__ = "profile_field_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id = Column(
        Integer,
        ForeignKey("profile_field_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value = Column(Text, nullable=True)
    visibility = Column(String(32), default="public", nullable=False)
    moderation_status = Column(
        String(16), default="approved", nullable=False
    )
    moderated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    field_definition = relationship("ProfileFieldDefinition", back_populates="values")

    __table_args__ = (
        UniqueConstraint("user_id", "field_id", name="uq_user_field_value"),
        Index("idx_pfv_user_id", "user_id"),
        Index("idx_pfv_field_id", "field_id"),
        Index("idx_pfv_moderation", "moderation_status", "updated_at"),
    )


# ── Profile Value Versions (audit trail) ──


class ProfileValueVersion(Base):
    __tablename__ = "profile_value_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id = Column(
        Integer,
        ForeignKey("profile_field_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_source = Column(
        String(32), default="user", nullable=False
    )
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_pvv_user_field", "user_id", "field_id"),
        Index("idx_pvv_changed_at", "changed_at"),
    )


# ── Profile Search Index (with full-text support) ──


class ProfileSearchIndex(Base):
    __tablename__ = "profile_search_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_key = Column(String(64), nullable=False, index=True)
    value = Column(Text, nullable=True)
    numeric_value = Column(Float, nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_psi_user_field", "user_id", "field_key"),
        Index("idx_psi_field_value", "field_key", "value"),
        Index("idx_psi_field_numeric", "field_key", "numeric_value"),
        Index("idx_psi_search_vector", "search_vector", postgresql_using="gin"),
        Index("idx_psi_user_field_value", "user_id", "field_key", "value"),
    )
