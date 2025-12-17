"""
Pydantic Schemas
Request and response models for API validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================== AUTHENTICATION SCHEMAS ====================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ==================== USER SCHEMAS ====================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str
    organization_id: int
    role: Optional[str] = "teacher"


class User(UserBase):
    id: int
    organization_id: int
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ORGANIZATION SCHEMAS ====================

class OrganizationBase(BaseModel):
    name: str
    contact_email: EmailStr
    contact_name: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    subscription_tier: Optional[str] = "trial"
    max_monthly_lessons: Optional[int] = 50


class Organization(OrganizationBase):
    id: int
    subscription_tier: str
    max_monthly_lessons: int
    is_active: bool
    total_lessons_generated: int
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationUsage(BaseModel):
    organization_id: int
    monthly_lessons_used: int
    monthly_lessons_limit: int
    total_lessons: int
    active_users: int
    subscription_tier: str


# ==================== LESSON PLAN SCHEMAS ====================

class LessonPlanRequest(BaseModel):
    grade_level: str
    subject: str
    teks_standard: str  # Now REQUIRED (not Optional)
    learning_objective: str
    duration: int = 45
    language: str = "bilingual"  # english, spanish, bilingual
    teacher_notes: Optional[str] = None  # Optional custom instructions from teacher
    
    # NEW: Section selection (teacher can choose which sections to generate)
    include_main_lesson: bool = True
    include_guided_practice: bool = True
    include_independent_practice: bool = True
    include_learning_stations: bool = False  # Optional for Math/ELA only
    include_small_group: bool = False  # Optional for Math/ELA only
    include_tier2: bool = False  # Optional for Math/ELA only
    include_tier3: bool = False  # Optional for Math/ELA only


class LessonPlanBase(BaseModel):
    grade_level: str
    subject: str
    teks_standard: Optional[str] = None
    learning_objective: str
    duration: int
    language: str = "bilingual"


class LessonPlan(LessonPlanBase):
    id: int
    user_id: int
    organization_id: int
    lesson_content: Dict[str, Any]
    api_cost: float
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ADMIN SCHEMAS ====================

class AdminStats(BaseModel):
    total_organizations: int
    total_users: int
    total_lessons: int
    monthly_lessons: int
    total_api_cost: float
