from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# ── Lookup Tables ──


class LookupItemOut(BaseModel):
    value: str
    label: str
    label_hi: Optional[str] = None
    display_order: int = 0
    is_active: bool = True

    model_config = {"from_attributes": True}


class LookupItemUpsert(BaseModel):
    value: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    label_hi: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


# ── Section ──


class ProfileSectionOut(BaseModel):
    id: int
    key: str
    name: str
    name_hi: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int
    completion_weight: float
    visibility_rule: Optional[dict] = None
    min_app_version: Optional[str] = None
    is_active: bool
    is_system: bool
    fields: list["ProfileFieldDefinitionOut"] = []

    model_config = {"from_attributes": True}


class ProfileSectionUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    name_hi: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    completion_weight: float = 1.0
    visibility_rule: Optional[dict] = None
    min_app_version: Optional[str] = None
    is_active: bool = True


# ── Field Definition ──


class ValidationRules(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[list[str]] = None
    date_min: Optional[str] = None
    date_max: Optional[str] = None


class ProfileFieldDefinitionOut(BaseModel):
    id: int
    section_id: int
    key: str
    label: str
    label_hi: Optional[str] = None
    field_type: str
    is_required: bool
    is_searchable: bool
    is_editable: bool
    is_visible: bool
    display_order: int
    default_value: Optional[str] = None
    lookup_table: Optional[str] = None
    options: Optional[list[dict[str, str]]] = None
    validation_rules: Optional[ValidationRules] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    pii: bool
    encrypt_at_rest: bool
    default_visibility: str
    completion_weight: float
    is_active: bool
    is_system: bool

    model_config = {"from_attributes": True}


class ProfileFieldDefinitionUpsert(BaseModel):
    section_id: Optional[int] = None
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    label_hi: Optional[str] = None
    field_type: str = "text"
    is_required: bool = False
    is_searchable: bool = False
    is_editable: bool = True
    is_visible: bool = True
    display_order: int = 0
    default_value: Optional[str] = None
    lookup_table: Optional[str] = None
    options: Optional[list[dict[str, str]]] = None
    validation_rules: Optional[ValidationRules] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    pii: bool = False
    encrypt_at_rest: bool = False
    default_visibility: str = "public"
    completion_weight: float = 1.0
    is_active: bool = True

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        allowed = {
            "text", "textarea", "integer", "decimal", "boolean",
            "date", "select", "multi-select", "radio", "checkbox",
            "lookup",
        }
        if v not in allowed:
            raise ValueError(f"field_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("default_visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        allowed = {"public", "matches_only", "premium_only", "private", "hidden"}
        if v not in allowed:
            raise ValueError(f"default_visibility must be one of: {', '.join(sorted(allowed))}")
        return v


class ProfileFieldDefinitionPatch(BaseModel):
    label: Optional[str] = None
    label_hi: Optional[str] = None
    field_type: Optional[str] = None
    is_required: Optional[bool] = None
    is_searchable: Optional[bool] = None
    is_editable: Optional[bool] = None
    is_visible: Optional[bool] = None
    display_order: Optional[int] = None
    default_value: Optional[str] = None
    lookup_table: Optional[str] = None
    options: Optional[list[dict[str, str]]] = None
    validation_rules: Optional[ValidationRules] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    pii: Optional[bool] = None
    encrypt_at_rest: Optional[bool] = None
    default_visibility: Optional[str] = None
    completion_weight: Optional[float] = None
    is_active: Optional[bool] = None
    section_id: Optional[int] = None


# ── Field Values (user-facing) ──


class ProfileFieldValueItem(BaseModel):
    field_id: int
    field_key: str
    label: str
    field_type: str
    value: Optional[str] = None
    options: Optional[list[dict[str, str]]] = None
    is_required: bool
    is_editable: bool = True
    visibility: str = "public"
    moderation_status: str = "approved"
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    unit: Optional[str] = None
    completion_weight: float = 1.0


class SectionProfileOut(BaseModel):
    section_id: int
    section_key: str
    section_name: str
    icon: Optional[str] = None
    display_order: int
    completion_weight: float
    fields: list[ProfileFieldValueItem]


class UpdateSectionRequest(BaseModel):
    fields: list[dict[str, Any]] = Field(
        default=[],
        description='List of {"field_id": int, "value": str, "visibility": str|null} objects',
    )

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: list) -> list:
        for item in v:
            if "field_id" not in item:
                raise ValueError("Each field must have 'field_id'")
            if not isinstance(item.get("field_id"), int):
                raise ValueError("field_id must be an integer")
        return v


class BulkUpdateProfileRequest(BaseModel):
    sections: list["BulkSectionUpdate"]


class BulkSectionUpdate(BaseModel):
    section_key: str
    fields: list[dict[str, Any]]


# ── Profile Completion ──


class ProfileCompletionOut(BaseModel):
    overall_percentage: float
    sections: list["SectionCompletionOut"]


class SectionCompletionOut(BaseModel):
    section_key: str
    section_name: str
    completion_percentage: float
    filled_count: int
    total_count: int
    weighted_score: float


# ── Full Profile ──


class FullProfileOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    city: str
    bio: Optional[str] = None
    intent: str
    profile_complete: bool
    completion: ProfileCompletionOut
    sections: list[SectionProfileOut]


# ── Version History ──


class ProfileValueVersionOut(BaseModel):
    id: int
    field_key: Optional[str] = None
    field_label: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_source: str
    changed_at: datetime

    model_config = {"from_attributes": True}


# ── Moderation ──


class ModerationAction(BaseModel):
    field_id: int
    action: str  # "approve", "reject", "request_review"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject", "request_review"):
            raise ValueError("action must be: approve, reject, request_review")
        return v


# ── Editable / Searchable field lists ──


class EditableFieldsOut(BaseModel):
    sections: list[SectionProfileOut]


class SearchableFieldsOut(BaseModel):
    fields: list["SearchableFieldItem"]


class SearchableFieldItem(BaseModel):
    key: str
    label: str
    field_type: str
    lookup_table: Optional[str] = None
    options: Optional[list[dict[str, str]]] = None
    unit: Optional[str] = None


class ValidationMetadataOut(BaseModel):
    field_id: int
    field_key: str
    validation_rules: Optional[ValidationRules] = None
    is_required: bool
    field_type: str
    options: Optional[list[dict[str, str]]] = None
