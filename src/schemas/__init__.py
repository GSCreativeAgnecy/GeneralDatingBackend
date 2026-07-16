from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Auth ──

class SendOtpRequest(BaseModel):
    phone_number: str = Field(min_length=10, max_length=15)


class VerifyOtpRequest(BaseModel):
    phone_number: str
    otp: str


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[str] = None
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)
    first_name: str = Field(min_length=2, max_length=50)
    phone_number: Optional[str] = None


class EmailLoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Profile ──

class SetupProfileRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=50)
    last_name: Optional[str] = None
    date_of_birth: str
    gender: str
    intent: str = "lets_see"
    city: str
    bio: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    languages: list[str] = []
    preferred_language: str = "en"


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mother_tongue: Optional[str] = None
    diet: Optional[str] = None
    drinking: Optional[str] = None
    smoking: Optional[str] = None
    sub_caste: Optional[str] = None
    annual_income: Optional[str] = None
    profile_created_by: Optional[str] = None
    contact_visibility: Optional[str] = None
    body_type: Optional[str] = None
    complexion: Optional[str] = None
    physical_status: Optional[str] = None
    horoscope_match: Optional[bool] = None
    nakshatra: Optional[str] = None
    rashi: Optional[str] = None
    gothram: Optional[str] = None
    dosham: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    family_type: Optional[str] = None
    family_values: Optional[str] = None
    about_family: Optional[str] = None
    father_occupation: Optional[str] = None
    mother_occupation: Optional[str] = None
    brothers: Optional[int] = None
    sisters: Optional[int] = None
    family_location: Optional[str] = None
    match_request_mode: Optional[bool] = None
    bio: Optional[str] = None
    intent: Optional[str] = None
    city: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    preferred_language: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


class UpdateLanguagesRequest(BaseModel):
    languages: list[str]


class ReorderPhotosRequest(BaseModel):
    photo_ids: list[int]


class UserLanguageOut(BaseModel):
    language: str
    model_config = {"from_attributes": True}


class UserPhotoOut(BaseModel):
    id: int
    photo_url: str
    is_primary: bool
    sort_order: int
    model_config = {"from_attributes": True}


class UserProfileOut(BaseModel):
    id: int
    first_name: str
    last_name: str = ""
    mother_tongue: str = ""
    diet: str = ""
    drinking: str = ""
    smoking: str = ""
    body_type: str = ""
    complexion: str = ""
    physical_status: str = ""
    nakshatra: str = ""
    rashi: str = ""
    family_type: str = ""
    family_values: str = ""
    horoscope_match: bool = False
    date_of_birth: str
    gender: str
    bio: Optional[str] = None
    intent: str
    city: str
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    phone_verified: bool
    photo_verified: bool
    profile_complete: bool
    is_premium: bool
    preferred_language: str
    show_online_status: bool
    last_active: Optional[datetime] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class UserSummaryOut(BaseModel):
    id: int
    first_name: str
    age: int
    gender: str
    city: str
    intent: str
    photo_verified: bool
    model_config = {"from_attributes": True}


# ── Discovery ──

class DiscoveryProfileOut(BaseModel):
    id: int
    first_name: str
    mother_tongue: str = ""
    diet: str = ""
    drinking: str = ""
    smoking: str = ""
    nakshatra: str = ""
    rashi: str = ""
    family_type: str = ""
    family_values: str = ""
    age: int
    gender: str
    city: str
    intent: str
    bio: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    photo_verified: bool
    distance_km: Optional[float] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    model_config = {"from_attributes": True}


# ── Swipes ──

class SwipeRequest(BaseModel):
    swiped_id: int
    direction: str


class SwipeStatsOut(BaseModel):
    likes_remaining: int
    super_likes_remaining: int


# ── Matches ──

class MatchOut(BaseModel):
    id: int
    matched_at: datetime
    is_active: bool
    user: UserSummaryOut
    model_config = {"from_attributes": True}


# ── Messages ──

class MessageOut(BaseModel):
    id: int
    match_id: int
    sender_id: int
    message_type: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageListItem(BaseModel):
    id: int
    match_id: int
    sender_id: int
    message_type: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    message_type: str = "text"
    content: str


class WomenFirstStatus(BaseModel):
    can_send: bool
    reason: Optional[str] = None


# ── Family Share ──

class FamilyShareRequest(BaseModel):
    shared_with_email: Optional[str] = None
    shared_with_phone: Optional[str] = None


class FamilyShareOut(BaseModel):
    id: int
    profile_user_id: int
    share_url: str
    expires_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class SharedProfileOut(BaseModel):
    first_name: str
    age: int
    city: str
    intent: str
    bio: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    photos: list[UserPhotoOut] = []


# ── Verification ──

class VerificationStatusOut(BaseModel):
    phone_verified: bool
    photo_verified: bool


# ── Preferences ──

class PreferencesOut(BaseModel):
    id: int
    min_age: int
    preferred_height_min: Optional[int] = None
    preferred_height_max: Optional[int] = None
    preferred_marital_status: str = ""
    preferred_mother_tongue: str = ""
    preferred_caste: str = ""
    preferred_diet: str = ""
    preferred_country: str = ""
    preferred_state: str = ""
    preferred_employed_in: str = ""
    preferred_education: str = ""
    preferred_physical_status: str = ""
    preferred_family_values: str = ""
    max_age: int
    preferred_gender: str
    max_distance_km: int
    intent_filter: Optional[str] = None
    city_filter: Optional[str] = None
    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    preferred_height_min: Optional[int] = None
    preferred_height_max: Optional[int] = None
    preferred_marital_status: Optional[str] = None
    preferred_mother_tongue: Optional[str] = None
    preferred_caste: Optional[str] = None
    preferred_diet: Optional[str] = None
    preferred_country: Optional[str] = None
    preferred_state: Optional[str] = None
    preferred_employed_in: Optional[str] = None
    preferred_education: Optional[str] = None
    preferred_physical_status: Optional[str] = None
    preferred_family_values: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    preferred_gender: Optional[str] = None
    max_distance_km: Optional[int] = None
    intent_filter: Optional[str] = None
    city_filter: Optional[str] = None


class UpdateNotificationSettingsRequest(BaseModel):
    show_online_status: Optional[bool] = None
    show_distance: Optional[bool] = None


# ── Notifications ──

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str] = None
    is_read: bool
    related_user_id: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Reports & Blocks ──

class ReportRequest(BaseModel):
    reported_id: int
    reason: Optional[str] = None


class BlockedUserOut(BaseModel):
    id: int
    name: str
    blocked_at: datetime
    model_config = {"from_attributes": True}


# ── Subscriptions ──

class SubscriptionOut(BaseModel):
    id: int
    plan_type: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class SubscriptionOrderOut(BaseModel):
    order_id: str
    amount: int
    currency: str = "INR"
    key_id: str = ""


class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str
    plan_id: Optional[int] = None


# ── Admin ──

class AdminDashboardOut(BaseModel):
    total_users: int
    active_users_today: int
    matches_today: int
    reports_pending: int
    premium_users: int = 0
    total_photos: int = 0
    total_swipes: int = 0
    total_messages: int = 0
    total_waitlist: int = 0
    total_matches: int = 0


class AdminReportOut(BaseModel):
    id: int
    reporter_id: int
    reported_id: int
    reporter_name: str = ""
    reported_name: str = ""
    reason: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminHandleReportRequest(BaseModel):
    action: str


class AdminUserOut(BaseModel):
    id: int
    first_name: str
    last_name: str = ""
    phone_number: str
    city: str
    gender: str = ""
    plan_name: str = "free"
    is_active: bool
    is_premium: bool
    phone_verified: bool = False
    photo_verified: bool = False
    profile_complete: bool = False
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminUserDetailOut(BaseModel):
    id: int
    first_name: str
    last_name: str = ""
    mother_tongue: str = ""
    diet: str = ""
    drinking: str = ""
    smoking: str = ""
    sub_caste: str = ""
    annual_income: str = ""
    profile_created_by: str = ""
    contact_visibility: str = ""
    body_type: str = ""
    complexion: str = ""
    physical_status: str = ""
    horoscope_match: bool = False
    nakshatra: str = ""
    rashi: str = ""
    gothram: str = ""
    dosham: str = ""
    time_of_birth: str = ""
    place_of_birth: str = ""
    horoscope_compatibility_score: Optional[int] = None
    family_type: str = ""
    family_values: str = ""
    about_family: Optional[str] = None
    father_occupation: str = ""
    mother_occupation: str = ""
    brothers: int = 0
    sisters: int = 0
    family_location: str = ""
    match_request_mode: bool = False
    phone_number: str
    email: Optional[str] = None
    date_of_birth: str = ""
    gender: str = ""
    bio: Optional[str] = None
    intent: str = ""
    city: str = ""
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    caste: Optional[str] = None
    earnings: Optional[str] = None
    marital_status: Optional[str] = None
    siblings: Optional[str] = None
    favorite_color: Optional[str] = None
    favorite_sports: Optional[str] = None
    phone_verified: bool = False
    photo_verified: bool = False
    profile_complete: bool = False
    is_premium: bool = False
    is_active: bool = True
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    preferred_language: str = "en"
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None
    photos: list[UserPhotoOut] = []
    languages: list[UserLanguageOut] = []
    model_config = {"from_attributes": True}


class AdminPhotoOut(BaseModel):
    id: int
    user_id: int
    user_name: str = ""
    photo_url: str
    is_primary: bool = False
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AdminSubscriptionOut(BaseModel):
    id: int
    user_id: int
    user_name: str = ""
    plan_type: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class AdminChatOut(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    user1_name: str
    user2_name: str
    matched_at: datetime
    is_active: bool
    message_count: int
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None


class AdminMessageOut(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    message_type: str
    content: str
    is_read: bool
    created_at: datetime


class AdminMatchUpdateRequest(BaseModel):
    is_active: Optional[bool] = None


class AdminUserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None
    photo_verified: Optional[bool] = None


class AdminPlanOut(BaseModel):
    id: int
    name: str
    price_paise: int
    duration_days: int
    swipes_per_day: Optional[int] = None
    super_likes_per_day: Optional[int] = None
    messages: bool = False
    photos_in_inbox_per_day: Optional[int] = None
    max_profile_photos: Optional[int] = None
    boosts_per_month: Optional[int] = None
    see_who_liked_you: bool = False
    no_ads: bool = False
    read_receipts: bool = False
    incognito_mode: bool = False
    verified_badge: bool = False
    is_active: bool
    sort_order: int
    model_config = {"from_attributes": True}


class AdminPlanSaveRequest(BaseModel):
    name: str
    price_paise: int = 0
    duration_days: int = 30
    swipes_per_day: Optional[int] = None
    super_likes_per_day: Optional[int] = None
    messages: bool = False
    photos_in_inbox_per_day: Optional[int] = None
    max_profile_photos: Optional[int] = None
    boosts_per_month: Optional[int] = None
    see_who_liked_you: bool = False
    no_ads: bool = False
    read_receipts: bool = False
    incognito_mode: bool = False
    verified_badge: bool = False
    is_active: bool = True
    sort_order: int = 0


class AdminCreateMatchRequest(BaseModel):
    user1_id: int
    user2_id: int


class AdminCreateUserRequest(BaseModel):
    phone_number: str = Field(min_length=10, max_length=15)
    first_name: str = Field(min_length=2, max_length=50)
    last_name: str = ""
    mother_tongue: str = ""
    diet: str = ""
    drinking: str = ""
    smoking: str = ""
    body_type: str = ""
    physical_status: str = ""
    date_of_birth: str = ""
    gender: str = ""
    city: str = ""
    bio: Optional[str] = None
    caste: Optional[str] = None
    earnings: Optional[str] = None
    marital_status: Optional[str] = None
    siblings: Optional[str] = None
    favorite_color: Optional[str] = None
    favorite_sports: Optional[str] = None
    is_premium: bool = False


class AdminEditUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mother_tongue: Optional[str] = None
    diet: Optional[str] = None
    drinking: Optional[str] = None
    smoking: Optional[str] = None
    sub_caste: Optional[str] = None
    annual_income: Optional[str] = None
    profile_created_by: Optional[str] = None
    contact_visibility: Optional[str] = None
    body_type: Optional[str] = None
    complexion: Optional[str] = None
    physical_status: Optional[str] = None
    horoscope_match: Optional[bool] = None
    nakshatra: Optional[str] = None
    rashi: Optional[str] = None
    gothram: Optional[str] = None
    dosham: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    family_type: Optional[str] = None
    family_values: Optional[str] = None
    about_family: Optional[str] = None
    father_occupation: Optional[str] = None
    mother_occupation: Optional[str] = None
    brothers: Optional[int] = None
    sisters: Optional[int] = None
    family_location: Optional[str] = None
    match_request_mode: Optional[bool] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    intent: Optional[str] = None
    college: Optional[str] = None
    workplace: Optional[str] = None
    height_cm: Optional[int] = None
    religion: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    caste: Optional[str] = None
    earnings: Optional[str] = None
    marital_status: Optional[str] = None
    siblings: Optional[str] = None
    favorite_color: Optional[str] = None
    favorite_sports: Optional[str] = None
    preferred_language: Optional[str] = None
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None
    photo_verified: Optional[bool] = None


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class AdminAssignPlanRequest(BaseModel):
    plan_id: int


class AdminUserStatsOut(BaseModel):
    total_swipes: int = 0
    total_likes: int = 0
    total_passes: int = 0
    total_matches: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_photos: int = 0
    total_reports_filed: int = 0
    total_reports_against: int = 0
    total_blocks: int = 0
    account_age_days: int = 0
    subscription_active: bool = False
    subscription_plan: str = "free"
    subscription_ends: Optional[datetime] = None
    last_active: Optional[datetime] = None


class AdminSwipeItem(BaseModel):
    id: int
    target_id: int
    target_name: str
    direction: str
    matched: bool = False
    created_at: datetime


class AdminMatchItem(BaseModel):
    id: int
    other_id: int
    other_name: str
    other_gender: str = ""
    other_city: str = ""
    is_active: bool
    message_count: int = 0
    matched_at: datetime


class AdminMessageItem(BaseModel):
    id: int
    match_id: int
    receiver_id: int
    receiver_name: str
    content: str
    is_read: bool
    created_at: datetime


class AdminPaginatedSwipes(BaseModel):
    items: list[AdminSwipeItem]
    total: int


class AdminPaginatedMatches(BaseModel):
    items: list[AdminMatchItem]
    total: int


class AdminPaginatedMessages(BaseModel):
    items: list[AdminMessageItem]
    total: int


class AdminLimitsOut(BaseModel):
    max_photos_per_user: int
    max_photo_size_mb: int
    family_share_expire_days: int


class AdminLimitsUpdateRequest(BaseModel):
    max_photos_per_user: Optional[int] = None
    max_photo_size_mb: Optional[int] = None
    family_share_expire_days: Optional[int] = None


class AdminWaitlistOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Admin Settings (White-Label) ──

HEX_COLOR_REGEX = r"^#([A-Fa-f0-9]{6})$"

ALLOWED_CURRENCIES = ["INR", "USD", "EUR", "GBP", "CAD", "AUD"]
ALLOWED_PAYMENT_PROCESSORS = ["stripe", "razorpay", "paypal", "helcim"]
ALLOWED_OTP_PROVIDERS = ["twilio", "android_sms_gateway"]


class BrandingSettingsUpdate(BaseModel):
    app_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None


class CurrencySettingUpdate(BaseModel):
    currency: str


# ── OTP Provider Settings ──

class TwilioSettingsUpdate(BaseModel):
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone: Optional[str] = None


class AndroidSmsSettingsUpdate(BaseModel):
    android_sms_gateway_url: Optional[str] = None
    android_sms_gateway_api_key: Optional[str] = None


class OtpProviderUpdate(BaseModel):
    preferred_otp_provider: str


# ── SMTP Settings ──

class SmtpSettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_name: Optional[str] = None
    notify_email: Optional[str] = None


# ── Payment Processor Settings ──

class StripeSettingsUpdate(BaseModel):
    stripe_secret_key: Optional[str] = None
    stripe_public_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None


class RazorpaySettingsUpdate(BaseModel):
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None


class PaypalSettingsUpdate(BaseModel):
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    paypal_webhook_id: Optional[str] = None
    paypal_mode: Optional[str] = None  # "sandbox" or "live"


class HelcimSettingsUpdate(BaseModel):
    helcim_api_token: Optional[str] = None
    helcim_account_id: Optional[str] = None
    helcim_webhook_secret: Optional[str] = None
    helcim_mode: Optional[str] = None  # "sandbox" or "live"


class ActivePaymentProcessorsUpdate(BaseModel):
    active_payment_processors: list[str]  # e.g. ["stripe", "razorpay"]


class SettingsDashboardResponse(BaseModel):
    app_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    logo_url: str = ""
    default_currency: str
    # Payment processors
    active_payment_processors: list[str] = []
    # Stripe
    stripe_public_key: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    # PayPal
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""
    paypal_mode: str = "sandbox"
    # Helcim
    helcim_api_token: str = ""
    helcim_account_id: str = ""
    helcim_webhook_secret: str = ""
    helcim_mode: str = "sandbox"
    # OTP Provider
    preferred_otp_provider: str = ""
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone: str = ""
    # Android SMS Gateway
    android_sms_gateway_url: str = ""
    android_sms_gateway_api_key: str = ""
    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = ""
    notify_email: str = ""


# ── Common ──

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
