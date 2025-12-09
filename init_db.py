"""
Initial Setup Script
Creates the first super admin user and organization
Run this after deploying to set up your platform
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from auth import get_password_hash

def init_db():
    """Initialize database with first organization and super admin"""
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if super admin already exists
        existing_admin = db.query(models.User).filter(
            models.User.role == "super_admin"
        ).first()
        
        if existing_admin:
            print("❌ Super admin already exists!")
            print(f"   Email: {existing_admin.email}")
            return
        
        # Create Edu-SmartAI organization (your company)
        org = models.Organization(
            name="Edu-SmartAI",
            contact_email="admin@edu-smartai.com",
            contact_name="Administrator",
            subscription_tier="enterprise",
            max_monthly_lessons=999999,  # Unlimited for admin
            is_active=True
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        
        print("✅ Created Edu-SmartAI organization")
        
        # Create super admin user
        admin_email = input("\nEnter super admin email: ").strip()
        admin_password = input("Enter super admin password: ").strip()
        admin_name = input("Enter super admin full name: ").strip()
        
        if not admin_email or not admin_password or not admin_name:
            print("❌ All fields are required!")
            return
        
        admin_user = models.User(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name=admin_name,
            role="super_admin",
            organization_id=org.id,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        
        print("\n" + "="*50)
        print("✅ SETUP COMPLETE!")
        print("="*50)
        print(f"Super Admin Email: {admin_email}")
        print(f"Organization ID: {org.id}")
        print("\nYou can now:")
        print("1. Login to the admin dashboard")
        print("2. Create charter school organizations")
        print("3. Add teachers to organizations")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def create_demo_org():
    """Create a demo organization with sample data"""
    db = SessionLocal()
    
    try:
        # Create demo charter school
        demo_org = models.Organization(
            name="Demo Charter School",
            contact_email="demo@charterschool.edu",
            contact_name="Demo Principal",
            subscription_tier="pro",
            max_monthly_lessons=500,
            is_active=True
        )
        db.add(demo_org)
        db.commit()
        db.refresh(demo_org)
        
        print(f"✅ Created demo organization (ID: {demo_org.id})")
        
        # Create demo teacher
        demo_teacher = models.User(
            email="teacher@demo.edu",
            hashed_password=get_password_hash("demo123"),
            full_name="Demo Teacher",
            role="teacher",
            organization_id=demo_org.id,
            is_active=True
        )
        db.add(demo_teacher)
        db.commit()
        
        print("✅ Created demo teacher")
        print(f"   Email: teacher@demo.edu")
        print(f"   Password: demo123")
        
    except Exception as e:
        print(f"❌ Error creating demo: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Edu-SmartAI Initial Setup")
    print("="*50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        create_demo_org()
    else:
        init_db()
