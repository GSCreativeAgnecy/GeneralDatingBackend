from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    # ── Identity & Auth ──
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    phone_verified = Column(Boolean, default=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True, default="")
    date_of_birth = Column(String, nullable=False)
    gender = Column(String, nullable=False)

    # ── Core Profile (discovery-essential) ──
    bio = Column(Text, nullable=True)
    intent = Column(String, default="lets_see")
    city = Column(String, nullable=False, index=True)

    # ── Status ──
    photo_verified = Column(Boolean, default=False)
    profile_complete = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # ── Activity ──
    last_active = Column(DateTime(timezone=True), nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)

    # ── Preferences ──
    preferred_language = Column(String, default="en")
    show_online_status = Column(Boolean, default=True)
    show_distance = Column(Boolean, default=True)

    # ── Timestamps ──
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Legacy profile columns (kept for backward compatibility during v2 migration) ──
    mother_tongue = Column(String, nullable=True, default="")
    diet = Column(String, nullable=True, default="")
    drinking = Column(String, nullable=True, default="")
    smoking = Column(String, nullable=True, default="")
    sub_caste = Column(String, nullable=True, default="")
    annual_income = Column(String, nullable=True, default="")
    profile_created_by = Column(String, nullable=True, default="")
    contact_visibility = Column(String, nullable=True, default="")
    body_type = Column(String, nullable=True, default="")
    complexion = Column(String, nullable=True, default="")
    physical_status = Column(String, nullable=True, default="")
    horoscope_match = Column(Boolean, default=False)
    nakshatra = Column(String, nullable=True, default="")
    rashi = Column(String, nullable=True, default="")
    gothram = Column(String, nullable=True, default="")
    dosham = Column(String, nullable=True, default="")
    time_of_birth = Column(String, nullable=True, default="")
    place_of_birth = Column(String, nullable=True, default="")
    horoscope_compatibility_score = Column(Integer, nullable=True)
    family_type = Column(String, nullable=True, default="")
    family_values = Column(String, nullable=True, default="")
    about_family = Column(Text, nullable=True, default="")
    father_occupation = Column(String, nullable=True, default="")
    mother_occupation = Column(String, nullable=True, default="")
    brothers = Column(Integer, default=0)
    sisters = Column(Integer, default=0)
    family_location = Column(String, nullable=True, default="")
    match_request_mode = Column(Boolean, default=False)
    college = Column(String, nullable=True)
    workplace = Column(String, nullable=True)
    height_cm = Column(Integer, nullable=True)
    religion = Column(String, nullable=True)
    education = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    caste = Column(String, nullable=True)
    earnings = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    siblings = Column(String, nullable=True)
    favorite_color = Column(String, nullable=True)
    favorite_sports = Column(String, nullable=True)

    photos = relationship("UserPhoto", back_populates="user", cascade="all, delete-orphan")
    languages = relationship("UserLanguage", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    swipes_made = relationship(
        "Swipe", foreign_keys="Swipe.swiper_id", back_populates="swiper", cascade="all, delete-orphan"
    )
    swipes_received = relationship(
        "Swipe", foreign_keys="Swipe.swiped_id", back_populates="swiped", cascade="all, delete-orphan"
    )
    profile_field_values = relationship(
        "ProfileFieldValue",
        back_populates=None,
        foreign_keys="ProfileFieldValue.user_id",
        cascade="all, delete-orphan",
    )

    @property
    def display_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


class UserPhoto(Base):
    __tablename__ = "user_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="photos")


class UserLanguage(Base):
    __tablename__ = "user_languages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language = Column(String, nullable=False)

    user = relationship("User", back_populates="languages")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=50)
    preferred_gender = Column(String, default="all")
    max_distance_km = Column(Integer, default=50)
    intent_filter = Column(String, nullable=True)
    city_filter = Column(String, nullable=True)
    preferred_height_min = Column(Integer, nullable=True)
    preferred_height_max = Column(Integer, nullable=True)
    preferred_marital_status = Column(Text, nullable=True, default="")
    preferred_mother_tongue = Column(Text, nullable=True, default="")
    preferred_caste = Column(Text, nullable=True, default="")
    preferred_diet = Column(String, nullable=True, default="")
    preferred_country = Column(Text, nullable=True, default="")
    preferred_state = Column(Text, nullable=True, default="")
    preferred_employed_in = Column(Text, nullable=True, default="")
    preferred_education = Column(String, nullable=True, default="")
    preferred_physical_status = Column(String, nullable=True, default="")
    preferred_family_values = Column(String, nullable=True, default="")

    user = relationship("User", back_populates="preferences")


class Swipe(Base):
    __tablename__ = "swipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    swiper_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    swiped_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    direction = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("swiper_id", "swiped_id", name="uq_swipe_pair"),)

    swiper = relationship("User", foreign_keys=[swiper_id], back_populates="swipes_made")
    swiped = relationship("User", foreign_keys=[swiped_id], back_populates="swipes_received")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    matched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    unmatched_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("user1_id < user2_id", name="ck_match_order"),
        UniqueConstraint("user1_id", "user2_id", name="uq_match_pair"),
    )

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(String, default="text")
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    match = relationship("Match", back_populates="messages")
    sender = relationship("User")


class BlockReport(Base):
    __tablename__ = "blocks_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=True)
    type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("reporter_id", "reported_id", "type", name="uq_block_report"),)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    related_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FamilyShare(Base):
    __tablename__ = "family_shares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_email = Column(String, nullable=True)
    shared_with_phone = Column(String, nullable=True)
    access_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_type = Column(String, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    payment_id = Column(String, nullable=True, index=True)
    starts_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ends_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price_paise = Column(Integer, nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=30)
    swipes_per_day = Column(Integer, nullable=True)
    super_likes_per_day = Column(Integer, nullable=True)
    messages = Column(Boolean, default=False)
    photos_in_inbox_per_day = Column(Integer, nullable=True)
    max_profile_photos = Column(Integer, nullable=True)
    boosts_per_month = Column(Integer, nullable=True)
    see_who_liked_you = Column(Boolean, default=False)
    no_ads = Column(Boolean, default=False)
    read_receipts = Column(Boolean, default=False)
    incognito_mode = Column(Boolean, default=False)
    verified_badge = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)


class WaitlistSubscriber(Base):
    __tablename__ = "waitlist_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OtpRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String, nullable=False, index=True)
    otp = Column(String, nullable=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
