import asyncio
from sqlalchemy import select
from core.database import async_session, init_db, engine
from core.security import hash_password
from models import User, Plan, UserPreferences
from models.profile import (
    LookupCaste,
    LookupEducation,
    LookupLanguage,
    LookupOccupation,
    LookupReligion,
    ProfileFieldDefinition,
    ProfileSection,
)
from datetime import datetime, timezone


DEFAULT_PHONE = "0000000000"
DEFAULT_PASSWORD = "admin123"
DEFAULT_NAME = "Admin"

DEFAULT_PLANS = [
    {"name": "Free", "price_paise": 0, "duration_days": 0, "swipes_per_day": 50, "super_likes_per_day": 1, "messages": False, "photos_in_inbox_per_day": None, "max_profile_photos": 6, "boosts_per_month": None, "see_who_liked_you": False, "no_ads": False, "read_receipts": False, "incognito_mode": False, "verified_badge": False, "sort_order": 0},
    {"name": "Premium Monthly", "price_paise": 49900, "duration_days": 30, "swipes_per_day": 200, "super_likes_per_day": 5, "messages": True, "photos_in_inbox_per_day": None, "max_profile_photos": 9, "boosts_per_month": 1, "see_who_liked_you": True, "no_ads": True, "read_receipts": True, "incognito_mode": False, "verified_badge": False, "sort_order": 1},
    {"name": "Premium Yearly", "price_paise": 299900, "duration_days": 365, "swipes_per_day": None, "super_likes_per_day": None, "messages": True, "photos_in_inbox_per_day": None, "max_profile_photos": None, "boosts_per_month": 3, "see_who_liked_you": True, "no_ads": True, "read_receipts": True, "incognito_mode": True, "verified_badge": True, "sort_order": 2},
]

DEFAULT_SECTIONS = [
    ("basic_info",       "Basic Information",      10),
    ("personal_details", "Personal Details",       20),
    ("lifestyle",        "Lifestyle",              30),
    ("religion_caste",   "Religion & Caste",       40),
    ("horoscope",        "Horoscope",              50),
    ("education_career", "Education & Career",     60),
    ("family",           "Family Details",         70),
    ("location",         "Location",               80),
    ("about_me",         "About Me",               90),
]


def _seed_fields(db, sections: dict):
    sid = lambda k: sections.get(k)
    fields = [
        # basic_info
        {"section_id": sid("basic_info"), "key": "mother_tongue", "label": "Mother Tongue", "field_type": "lookup", "lookup_table": "languages", "is_searchable": True, "display_order": 1},
        {"section_id": sid("basic_info"), "key": "marital_status", "label": "Marital Status", "field_type": "select", "is_searchable": True, "display_order": 2, "options": [{"value": "never_married", "label": "Never Married"}, {"value": "divorced", "label": "Divorced"}, {"value": "widowed", "label": "Widowed"}]},
        {"section_id": sid("basic_info"), "key": "college", "label": "College", "field_type": "text", "is_searchable": True, "display_order": 3},
        {"section_id": sid("basic_info"), "key": "workplace", "label": "Workplace", "field_type": "text", "is_searchable": True, "display_order": 4},
        # personal_details
        {"section_id": sid("personal_details"), "key": "height_cm", "label": "Height (cm)", "field_type": "integer", "is_searchable": True, "unit": "cm", "display_order": 1, "validation_rules": {"min_value": 100, "max_value": 250}},
        {"section_id": sid("personal_details"), "key": "body_type", "label": "Body Type", "field_type": "select", "display_order": 2, "options": [{"value": "slim", "label": "Slim"}, {"value": "athletic", "label": "Athletic"}, {"value": "average", "label": "Average"}, {"value": "heavy", "label": "Heavy"}]},
        {"section_id": sid("personal_details"), "key": "complexion", "label": "Complexion", "field_type": "select", "display_order": 3, "options": [{"value": "very_fair", "label": "Very Fair"}, {"value": "fair", "label": "Fair"}, {"value": "wheatish", "label": "Wheatish"}, {"value": "dark", "label": "Dark"}]},
        {"section_id": sid("personal_details"), "key": "physical_status", "label": "Physical Status", "field_type": "select", "display_order": 4, "options": [{"value": "normal", "label": "Normal"}, {"value": "physically_challenged", "label": "Physically Challenged"}]},
        {"section_id": sid("personal_details"), "key": "siblings", "label": "Siblings", "field_type": "text", "display_order": 5},
        # lifestyle
        {"section_id": sid("lifestyle"), "key": "diet", "label": "Diet", "field_type": "select", "is_searchable": True, "display_order": 1, "options": [{"value": "vegetarian", "label": "Vegetarian"}, {"value": "non_vegetarian", "label": "Non-Vegetarian"}, {"value": "eggetarian", "label": "Eggetarian"}, {"value": "vegan", "label": "Vegan"}]},
        {"section_id": sid("lifestyle"), "key": "drinking", "label": "Drinking", "field_type": "select", "display_order": 2, "options": [{"value": "no", "label": "No"}, {"value": "occasionally", "label": "Occasionally"}, {"value": "yes", "label": "Yes"}]},
        {"section_id": sid("lifestyle"), "key": "smoking", "label": "Smoking", "field_type": "select", "display_order": 3, "options": [{"value": "no", "label": "No"}, {"value": "occasionally", "label": "Occasionally"}, {"value": "yes", "label": "Yes"}]},
        {"section_id": sid("lifestyle"), "key": "favorite_color", "label": "Favorite Color", "field_type": "text", "display_order": 4},
        {"section_id": sid("lifestyle"), "key": "favorite_sports", "label": "Favorite Sports", "field_type": "text", "display_order": 5},
        # religion_caste
        {"section_id": sid("religion_caste"), "key": "religion", "label": "Religion", "field_type": "lookup", "lookup_table": "religions", "is_searchable": True, "display_order": 1},
        {"section_id": sid("religion_caste"), "key": "caste", "label": "Caste", "field_type": "lookup", "lookup_table": "castes", "is_searchable": True, "display_order": 2},
        {"section_id": sid("religion_caste"), "key": "sub_caste", "label": "Sub Caste", "field_type": "text", "display_order": 3},
        {"section_id": sid("religion_caste"), "key": "gothram", "label": "Gothram", "field_type": "text", "display_order": 4},
        # horoscope
        {"section_id": sid("horoscope"), "key": "horoscope_match", "label": "Horoscope Match", "field_type": "boolean", "display_order": 1},
        {"section_id": sid("horoscope"), "key": "nakshatra", "label": "Nakshatra", "field_type": "text", "display_order": 2},
        {"section_id": sid("horoscope"), "key": "rashi", "label": "Rashi", "field_type": "text", "display_order": 3},
        {"section_id": sid("horoscope"), "key": "dosham", "label": "Dosham", "field_type": "text", "display_order": 4},
        {"section_id": sid("horoscope"), "key": "time_of_birth", "label": "Time of Birth", "field_type": "text", "pii": True, "encrypt_at_rest": True, "display_order": 5},
        {"section_id": sid("horoscope"), "key": "place_of_birth", "label": "Place of Birth", "field_type": "text", "pii": True, "encrypt_at_rest": True, "display_order": 6},
        # education_career
        {"section_id": sid("education_career"), "key": "education", "label": "Education", "field_type": "lookup", "lookup_table": "educations", "is_searchable": True, "display_order": 1},
        {"section_id": sid("education_career"), "key": "occupation", "label": "Occupation", "field_type": "lookup", "lookup_table": "occupations", "is_searchable": True, "display_order": 2},
        {"section_id": sid("education_career"), "key": "annual_income", "label": "Annual Income", "field_type": "text", "is_searchable": True, "display_order": 3},
        {"section_id": sid("education_career"), "key": "employed_in", "label": "Employed In", "field_type": "text", "is_searchable": True, "display_order": 4},
        # family
        {"section_id": sid("family"), "key": "family_type", "label": "Family Type", "field_type": "select", "display_order": 1, "options": [{"value": "joint", "label": "Joint"}, {"value": "nuclear", "label": "Nuclear"}]},
        {"section_id": sid("family"), "key": "family_values", "label": "Family Values", "field_type": "select", "display_order": 2, "options": [{"value": "traditional", "label": "Traditional"}, {"value": "moderate", "label": "Moderate"}, {"value": "liberal", "label": "Liberal"}]},
        {"section_id": sid("family"), "key": "father_occupation", "label": "Father Occupation", "field_type": "text", "display_order": 3},
        {"section_id": sid("family"), "key": "mother_occupation", "label": "Mother Occupation", "field_type": "text", "display_order": 4},
        {"section_id": sid("family"), "key": "brothers", "label": "Brothers", "field_type": "integer", "display_order": 5},
        {"section_id": sid("family"), "key": "sisters", "label": "Sisters", "field_type": "integer", "display_order": 6},
        {"section_id": sid("family"), "key": "family_location", "label": "Family Location", "field_type": "text", "display_order": 7},
        # location
        {"section_id": sid("location"), "key": "profile_created_by", "label": "Profile Created By", "field_type": "select", "display_order": 1, "options": [{"value": "self", "label": "Self"}, {"value": "parent", "label": "Parent"}, {"value": "sibling", "label": "Sibling"}, {"value": "friend", "label": "Friend"}]},
        {"section_id": sid("location"), "key": "contact_visibility", "label": "Contact Visibility", "field_type": "select", "default_visibility": "matches_only", "display_order": 2, "options": [{"value": "all", "label": "All"}, {"value": "matches", "label": "Matches Only"}, {"value": "none", "label": "Hidden"}]},
        {"section_id": sid("location"), "key": "match_request_mode", "label": "Match Request Mode", "field_type": "boolean", "display_order": 3},
        # about_me
        {"section_id": sid("about_me"), "key": "about_family", "label": "About My Family", "field_type": "textarea", "display_order": 1, "validation_rules": {"max_length": 2000}},
    ]
    for f in fields:
        if f.get("section_id"):
            db.add(ProfileFieldDefinition(**f, is_system=True))


def _seed_lookups(db):
    religions = [
        ("hindu", "Hindu", 1), ("muslim", "Muslim", 2), ("christian", "Christian", 3),
        ("sikh", "Sikh", 4), ("jain", "Jain", 5), ("buddhist", "Buddhist", 6),
        ("parsi", "Parsi", 7), ("jewish", "Jewish", 8), ("other", "Other", 9),
    ]
    for value, label, order in religions:
        db.add(LookupReligion(value=value, label=label, display_order=order))

    occupations = [
        ("software_engineer", "Software Engineer", 1), ("doctor", "Doctor", 2),
        ("teacher", "Teacher", 3), ("business_owner", "Business Owner", 4),
        ("manager", "Manager", 5), ("accountant", "Accountant", 6),
        ("lawyer", "Lawyer", 7), ("civil_engineer", "Civil Engineer", 8),
        ("government", "Government Service", 9), ("student", "Student", 10),
        ("other", "Other", 99),
    ]
    for value, label, order in occupations:
        db.add(LookupOccupation(value=value, label=label, display_order=order))

    educations = [
        ("high_school", "High School", 1), ("bachelors", "Bachelors Degree", 2),
        ("masters", "Masters Degree", 3), ("phd", "Ph.D / Doctorate", 4),
        ("diploma", "Diploma", 5), ("professional", "Professional Degree", 6),
        ("other", "Other", 99),
    ]
    for value, label, order in educations:
        db.add(LookupEducation(value=value, label=label, display_order=order))

    languages = [
        ("hindi", "Hindi", 1), ("telugu", "Telugu", 2), ("tamil", "Tamil", 3),
        ("marathi", "Marathi", 4), ("gujarati", "Gujarati", 5), ("bengali", "Bengali", 6),
        ("kannada", "Kannada", 7), ("malayalam", "Malayalam", 8), ("punjabi", "Punjabi", 9),
        ("odia", "Odia", 10), ("urdu", "Urdu", 11), ("english", "English", 12),
        ("other", "Other", 99),
    ]
    for value, label, order in languages:
        db.add(LookupLanguage(value=value, label=label, display_order=order))


async def seed():
    await init_db()

    async with async_session() as db:
        # ── Plans ──
        plans_exist = (await db.execute(select(Plan))).scalars().first()
        if not plans_exist:
            for p in DEFAULT_PLANS:
                db.add(Plan(**p))
            await db.flush()
            print("Default subscription plans created.")

        # ── Profile Sections ──
        sections_exist = (await db.execute(select(ProfileSection))).scalars().first()
        if not sections_exist:
            for key, name, order in DEFAULT_SECTIONS:
                db.add(ProfileSection(key=key, name=name, display_order=order))
            await db.flush()
            print("Default profile sections created.")

            # Seed field definitions
            sections_map = {}
            result = await db.execute(select(ProfileSection))
            for s in result.scalars().all():
                sections_map[s.key] = s.id

            _seed_fields(db, sections_map)
            print("Default profile fields created.")

        # ── Lookup Tables ──
        lookups_exist = (await db.execute(select(LookupReligion))).scalars().first()
        if not lookups_exist:
            _seed_lookups(db)
            print("Default lookup tables populated.")

        # ── Admin User ──
        result = await db.execute(select(User).where(User.phone_number == DEFAULT_PHONE))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Default account already exists (phone: {DEFAULT_PHONE})")
        else:
            user = User(
                phone_number=DEFAULT_PHONE,
                phone_verified=True,
                password_hash=hash_password(DEFAULT_PASSWORD),
                first_name=DEFAULT_NAME,
                date_of_birth="2000-01-01",
                gender="male",
                city="Mumbai",
                profile_complete=True,
                is_premium=True,
                photo_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()
            print("Default account created:")
            print(f"  Phone:    {DEFAULT_PHONE}")
            print(f"  Password: {DEFAULT_PASSWORD}")
            existing = user

        # Ensure admin has preferences
        pref_result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == existing.id)
        )
        if not pref_result.scalar_one_or_none():
            db.add(UserPreferences(
                user_id=existing.id,
                min_age=18,
                max_age=50,
                preferred_gender="all",
                max_distance_km=500,
            ))
            print("Admin preferences created (all genders, 18-50, 500km).")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
