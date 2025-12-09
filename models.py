"""
Database Models
SQLAlchemy models for the application
"""

from sqlalchemy import Boolean, Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Organization(Base):
    """Charter School / Organization Model"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    subscription_tier = Column(String(50), default="trial")  # trial, basic, pro, enterprise
    max_monthly_lessons = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    total_lessons_generated = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="organization")
    lesson_plans = relationship("LessonPlan", back_populates="organization")


class User(Base):
    """Teacher / User Model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="teacher")  # teacher, admin, super_admin
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    lesson_plans = relationship("LessonPlan", back_populates="user")


class LessonPlan(Base):
    """Generated Lesson Plan Model"""
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Lesson metadata
    grade_level = Column(String(10), nullable=False)
    subject = Column(String(100), nullable=False)
    teks_standard = Column(String(100))
    learning_objective = Column(Text, nullable=False)
    duration = Column(Integer, default=45)  # in minutes
    language = Column(String(20), default="bilingual")  # english, spanish, bilingual
    
    # Generated content (stored as JSON)
    lesson_content = Column(JSON, nullable=False)
    
    # Tracking
    api_cost = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="lesson_plans")
    organization = relationship("Organization", back_populates="lesson_plans")
