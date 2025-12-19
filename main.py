"""
Edu-SmartAI Lesson Plan Generator - Backend API
FastAPI server with secure OpenAI integration and multi-tenant support
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import os
from dotenv import load_dotenv
import openai
import json
import re

from database import get_db, engine
import models
import schemas
from auth import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user,
    get_current_active_user
)

# Import TEKS router
from modules.teks import router as teks_router

# Load environment variables
load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Edu-SmartAI API",
    description="AI-Powered Lesson Plan Generator for K-12 Education",
    version="1.0.0"
)

# ==================== UTF-8 JSON RESPONSE CLASS ====================
from fastapi.responses import JSONResponse

class UTF8JSONResponse(JSONResponse):
    """Custom JSON response ensuring UTF-8 encoding"""
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,  # CRITICAL: allows Spanish characters
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# Set as default response class for all routes
app.router.default_response_class = UTF8JSONResponse
# ====================================================================

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== UTF-8 ENCODING MIDDLEWARE ====================
@app.middleware("http")
async def enforce_utf8_encoding(request, call_next):
    """
    Ensures all HTTP responses use UTF-8 encoding.
    Fixes Spanish character display issues.
    """
    response = await call_next(request)
    
    # Force UTF-8 encoding for ALL content types
    if "content-type" in response.headers:
        content_type = response.headers["content-type"]
        # Remove existing charset before adding UTF-8
        if "charset" in content_type:
            content_type = content_type.split(";")[0].strip()
        response.headers["content-type"] = f"{content_type}; charset=utf-8"
    else:
        response.headers["content-type"] = "application/json; charset=utf-8"
    
    return response
# ====================================================================

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Include TEKS router
app.include_router(teks_router)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ==================== HELPER FUNCTIONS ====================

def detect_teacher_request_type(teacher_notes: str, subject: str) -> str:
    """
    Detect what type of content the teacher is requesting
    
    Returns:
        'story' - Generate 400-600 word narrative (ELA)
        'math_problems' - Create math word problems (Math)
        'scenarios' - Include scenarios/facts (Science/SS)
        'standard' - Regular anticipatory set
    """
    if not teacher_notes:
        return 'standard'
    
    notes_lower = teacher_notes.lower()
    
    # Story keywords (primarily for ELA)
    story_keywords = ['story', 'narrative', 'create a story', 'write about', 'tale', 
                      'fiction', 'character', 'plot', 'cuento', 'narrativa']
    
    # Math problem keywords
    math_keywords = ['problem', 'word problem', 'example', 'practice problem', 
                     'math problem', 'calculation', 'solve', 'compute']
    
    # Scenario/facts keywords
    scenario_keywords = ['scenario', 'fact', 'example', 'real-world', 'situation',
                        'case study', 'include', 'demonstrate']
    
    # Check for story request
    if any(keyword in notes_lower for keyword in story_keywords):
        return 'story'
    
    # Check for math problems (only for Math subjects)
    if 'math' in subject.lower() and any(keyword in notes_lower for keyword in math_keywords):
        return 'math_problems'
    
    # Check for scenarios (Science/Social Studies)
    if any(keyword in notes_lower for keyword in scenario_keywords):
        return 'scenarios'
    
    return 'standard'


def generate_story_prompt(teacher_notes: str, grade_level: str, subject: str, language: str) -> str:
    """Generate detailed story creation prompt"""
    
    grade_levels = {
        'K': 'kindergarten level (very simple sentences, 3-5 words per sentence, basic vocabulary)',
        '1': '1st grade level (simple sentences, 5-8 words per sentence, basic sight words)',
        '2': '2nd grade level (simple to moderate sentences, 8-12 words per sentence)',
        '3': '3rd grade level (moderate complexity, 10-15 words per sentence, expanding vocabulary)',
        '4': '4th grade level (moderate complexity with some complex sentences, varied vocabulary)',
        '5': '5th grade level (varied sentence complexity, academic vocabulary)',
        '6': '6th grade level (complex sentences, academic and subject-specific vocabulary)',
        '7': '7th grade level (sophisticated vocabulary, varied sentence structures)',
        '8': '8th grade level (advanced vocabulary, complex sentence structures)'
    }
    
    story_complexity = grade_levels.get(grade_level, '4th grade level')
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
🎯 STORY GENERATION REQUEST
═══════════════════════════════════════════════════════════════════════════════

TEACHER'S REQUEST: {teacher_notes}

🚨 CRITICAL: WRITE A COMPLETE 400-600 WORD NARRATIVE STORY 🚨

YOU MUST write the ACTUAL complete story in the "anticipatorySet" field.

NOT:
❌ "[Insert story here]"
❌ A 2-3 sentence summary
❌ A placeholder

YES:
✅ Complete 400-600 word narrative story
✅ Beginning, middle, and end
✅ Character dialogue: "I'm excited!" she said.
✅ Sensory details and emotions
✅ Written at {story_complexity}

STRUCTURE:
- Opening (100-150 words): Introduce characters, setting, situation
- Middle (200-300 words): Action, dialogue, events, emotions
- Ending (100-150 words): Resolution, learning moment

AFTER writing the story, integrate the characters into ALL practice problems and activities throughout the lesson.

═══════════════════════════════════════════════════════════════════════════════
"""


def generate_math_problems_prompt(teacher_notes: str, grade_level: str, teks_standard: str) -> str:
    """Generate math problems based on teacher request"""
    return f"""
═══════════════════════════════════════════════════════════════════════════════
📐 MATH PROBLEMS REQUEST
═══════════════════════════════════════════════════════════════════════════════

TEACHER'S REQUEST: {teacher_notes}

Create word problems based on:
- Grade {grade_level} level
- TEKS Standard: {teks_standard}
- Real-world contexts appropriate for this grade

Include the requested number and type of problems in:
- Guided Practice section (with step-by-step solutions)
- Independent Practice section (for students to solve)

Make problems engaging and relatable to {grade_level} graders.

═══════════════════════════════════════════════════════════════════════════════
"""


def generate_scenarios_prompt(teacher_notes: str, subject: str) -> str:
    """Generate scenarios/facts for Science or Social Studies"""
    return f"""
═══════════════════════════════════════════════════════════════════════════════
🔬 SCENARIOS / FACTS REQUEST
═══════════════════════════════════════════════════════════════════════════════

TEACHER'S REQUEST: {teacher_notes}

For this {subject} lesson:
- Include the requested scenarios, facts, or examples in the "directInstruction" section
- Make content engaging and age-appropriate
- Use real-world connections when possible
- Ensure accuracy and educational value

═══════════════════════════════════════════════════════════════════════════════
"""


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/auth/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user (teacher)"""
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if organization exists
    organization = db.query(models.Organization).filter(
        models.Organization.id == user.organization_id
    ).first()
    if not organization:
        raise HTTPException(status_code=400, detail="Organization not found")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        organization_id=user.organization_id,
        role=user.role or "teacher"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/api/auth/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


# ==================== ORGANIZATION ENDPOINTS ====================

@app.post("/api/organizations", response_model=schemas.Organization)
async def create_organization(
    org: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization (charter school)"""
    db_org = models.Organization(
        name=org.name,
        contact_email=org.contact_email,
        contact_name=org.contact_name,
        subscription_tier=org.subscription_tier or "trial",
        max_monthly_lessons=org.max_monthly_lessons or 50
    )
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


@app.get("/api/organizations/{org_id}", response_model=schemas.Organization)
async def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get organization details"""
    # Check if user belongs to this organization or is admin
    if current_user.organization_id != org_id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@app.get("/api/organizations/{org_id}/usage", response_model=schemas.OrganizationUsage)
async def get_organization_usage(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get organization usage statistics"""
    # Check permissions
    if current_user.organization_id != org_id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get current month's usage
    now = datetime.utcnow()
    first_day = datetime(now.year, now.month, 1)
    
    monthly_lessons = db.query(models.LessonPlan).filter(
        models.LessonPlan.organization_id == org_id,
        models.LessonPlan.created_at >= first_day
    ).count()
    
    total_lessons = db.query(models.LessonPlan).filter(
        models.LessonPlan.organization_id == org_id
    ).count()
    
    active_users = db.query(models.User).filter(
        models.User.organization_id == org_id,
        models.User.is_active == True
    ).count()
    
    return {
        "organization_id": org_id,
        "monthly_lessons_used": monthly_lessons,
        "monthly_lessons_limit": org.max_monthly_lessons,
        "total_lessons": total_lessons,
        "active_users": active_users,
        "subscription_tier": org.subscription_tier
    }


# ==================== LESSON PLAN ENDPOINTS ====================

@app.post("/api/lessons/generate", response_model=schemas.LessonPlan)
async def generate_lesson_plan(
    request: schemas.LessonPlanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate a new lesson plan using OpenAI"""
    
    # Validate grade level (K-8 only)
    valid_grades = ['K', '1', '2', '3', '4', '5', '6', '7', '8']
    if request.grade_level not in valid_grades:
        raise HTTPException(
            status_code=400,
            detail="Invalid grade level. Only Kindergarten through 8th grade are supported."
        )
    
    # Validate subject and grade restrictions
    valid_subjects = {
        'Mathematics': ['K', '1', '2', '3', '4', '5', '6', '7', '8'],
        'Advanced Mathematics': ['6', '7', '8'],
        'English Language Arts': ['K', '1', '2', '3', '4', '5', '6', '7', '8'],
        'Spanish Language Arts': ['K', '1', '2', '3', '4', '5'],
        'Science': ['K', '1', '2', '3', '4', '5', '6', '7', '8'],
        'Social Studies': ['K', '1', '2', '3', '4', '5', '6', '7', '8']
    }
    
    if request.subject not in valid_subjects:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid subject. Valid subjects are: {', '.join(valid_subjects.keys())}"
        )
    
    if request.grade_level not in valid_subjects[request.subject]:
        raise HTTPException(
            status_code=400,
            detail=f"{request.subject} is only available for grades {', '.join(valid_subjects[request.subject])}"
        )
    
    # Check organization usage limits
    org = db.query(models.Organization).filter(
        models.Organization.id == current_user.organization_id
    ).first()
    
    # Count this month's usage
    now = datetime.utcnow()
    first_day = datetime(now.year, now.month, 1)
    monthly_usage = db.query(models.LessonPlan).filter(
        models.LessonPlan.organization_id == current_user.organization_id,
        models.LessonPlan.created_at >= first_day
    ).count()
    
    if monthly_usage >= org.max_monthly_lessons:
        raise HTTPException(
            status_code=403,
            detail=f"Monthly limit of {org.max_monthly_lessons} lessons reached. Please upgrade your plan."
        )
    
    # Determine which sections to generate
    sections = request.sections if request.sections else ['mainLessonPlan', 'guidedPractice', 'independentPractice']
    
    # Detect teacher request type
    request_type = detect_teacher_request_type(request.teacher_notes or '', request.subject)
    
    # Generate the prompt
    language_instructions = {
        "english": "Generate all content in English only.",
        "spanish": "Generate all content in Spanish only. All sections, instructions, activities, and materials should be in Spanish.",
        "bilingual": """Generate all content in BILINGUAL format (English and Spanish side-by-side).
        
CRITICAL BILINGUAL FORMATTING RULES:
- For each section, provide BOTH English and Spanish versions
- Use this format for all text content:
  [EN]: English text here
  [ES]: Spanish text here
  
- For lists/arrays, provide bilingual items:
  "English item / Spanish item"
  or
  {"en": "English text", "es": "Spanish text"}
  
- Ensure Spanish translations are:
  * Culturally appropriate for Texas Hispanic students
  * Pedagogically sound (not just literal translations)
  * Use appropriate academic Spanish terms
  
- For materials lists, use bilingual format: "Material name (Nombre del material)"
- For TEKS standards, keep in English but explain in both languages"""
    }
    
    language_instruction = language_instructions.get(request.language, language_instructions["bilingual"])
    
    # Build section-specific prompts based on request type
    if request_type == 'story':
        anticipatory_set_instruction = '"anticipatorySet": "WRITE THE COMPLETE 400-600 WORD NARRATIVE STORY HERE. Include character names, dialogue in quotation marks, sensory details, beginning-middle-end structure. NOT a summary or placeholder - the actual full story."'
    else:
        anticipatory_set_instruction = '"anticipatorySet": "Brief engaging hook/introduction (2-4 sentences) to capture student interest and connect to prior knowledge"'
    
    section_prompts = {
        'mainLessonPlan': f"""
  "mainLessonPlan": {{
    "objective": "Clear, measurable learning objective aligned to TEKS (in requested language)",
    "materials": ["List of required materials (bilingual format if applicable)"],
    {anticipatory_set_instruction},
    "directInstruction": "Step-by-step teaching procedure with clear teacher actions and explanations",
    "modelingAndChecking": "How to model the concept and check for understanding throughout",
    "closure": "Summary and reflection activity to close the lesson"
  }}""",
        'guidedPractice': """
  "guidedPractice": {
    "description": "Detailed guided practice activities where teacher provides support",
    "activities": ["3-4 structured practice activities with teacher guidance"],
    "differentiationStrategies": ["Support strategies for diverse learners"]
  }""",
        'independentPractice': """
  "independentPractice": {
    "description": "Activities students complete with minimal assistance",
    "activities": ["3-4 independent practice tasks"],
    "assessmentCriteria": ["How to assess student work"]
  }""",
        'learningStations': """
  "learningStations": [
    {
      "stationName": "Station 1 name",
      "description": "What students do at this station",
      "materials": ["Required materials"],
      "instructions": "Step-by-step student instructions",
      "duration": "Recommended time"
    },
    {
      "stationName": "Station 2 name",
      "description": "Technology or hands-on activity",
      "materials": ["Required materials"],
      "instructions": "Clear directions",
      "duration": "Time allocation"
    },
    {
      "stationName": "Station 3 name",
      "description": "Application or extension activity",
      "materials": ["Materials needed"],
      "instructions": "Detailed steps",
      "duration": "Time needed"
    }
  ]""",
        'smallGroupInstruction': """
  "smallGroupInstruction": {
    "groupingStrategy": "How to group students (by skill level, etc.)",
    "focusArea": "Specific skill or concept to target",
    "activities": ["2-3 targeted small group activities"],
    "assessmentMethod": "How to monitor progress",
    "duration": "Recommended time per group"
  }""",
        'tier2Intervention': """
  "tier2Intervention": {
    "targetPopulation": "Which students need Tier 2 support",
    "interventionGoal": "Specific skill to address",
    "strategies": ["3-4 evidence-based intervention strategies"],
    "frequency": "How often to implement (e.g., 3x per week, 20 min)",
    "progressMonitoring": "How to track improvement",
    "resources": ["Materials and tools needed"]
  }""",
        'tier3Intervention': """
  "tier3Intervention": {
    "targetPopulation": "Students requiring intensive support",
    "interventionGoal": "Highly specific, measurable goal",
    "intensiveStrategies": ["3-4 intensive, individualized strategies"],
    "frequency": "Daily implementation schedule",
    "dataCollection": "Detailed progress monitoring plan",
    "collaborationPlan": "Who to involve (specialists, parents, etc.)",
    "resources": ["Specialized materials and supports"]
  }"""
    }
    
    # Build JSON structure based on selected sections
    selected_section_prompts = ',\n'.join([section_prompts[section] for section in sections if section in section_prompts])
    
    # Add teacher-specific instructions based on request type
    teacher_instructions = ""
    if request.teacher_notes:
        if request_type == 'story':
            teacher_instructions = generate_story_prompt(request.teacher_notes, request.grade_level, request.subject, request.language)
        elif request_type == 'math_problems':
            teacher_instructions = generate_math_problems_prompt(request.teacher_notes, request.grade_level, request.teks_standard or '')
        elif request_type == 'scenarios':
            teacher_instructions = generate_scenarios_prompt(request.teacher_notes, request.subject)
        else:
            teacher_instructions = f"\nTEACHER'S ADDITIONAL NOTES:\n{request.teacher_notes}\n"
    
    prompt = f"""You are an expert K-8 educator specializing in Texas curriculum design with expertise in bilingual education. Generate a comprehensive, standards-aligned lesson plan.

LANGUAGE REQUIREMENT: {language_instruction}

REQUIREMENTS:
- Grade Level: {request.grade_level}
- Subject: {request.subject}
- TEKS Standard: {request.teks_standard}
- Learning Objective: {request.learning_objective}
- Duration: {request.duration} minutes
- Language Mode: {request.language}

{teacher_instructions}

Generate a lesson plan with ONLY the following sections in JSON format:

{{
  "lessonTitle": "Engaging title for the lesson (bilingual if applicable)",
{selected_section_prompts}
}}

Make the content practical, engaging, and directly applicable to {request.grade_level} grade {request.subject}.

CRITICAL: If generating a story, write the complete 400-600 word narrative directly in the "anticipatorySet" field. Do not use placeholders."""

    try:
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert K-12 educator and curriculum designer specializing in Texas TEKS standards. Generate comprehensive, practical lesson plans in valid JSON format only. When asked to write a story, write the complete narrative directly in the JSON - never use placeholders. Do not include any text before or after the JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Extract and parse the response
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        content = content.replace("```json\n", "").replace("```\n", "").replace("```", "").strip()
        
        # Parse JSON
        lesson_content = json.loads(content)
        
        # Save to database
        db_lesson = models.LessonPlan(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            grade_level=request.grade_level,
            subject=request.subject,
            teks_standard=request.teks_standard,
            learning_objective=request.learning_objective,
            duration=request.duration,
            language=request.language,
            lesson_content=lesson_content,
            api_cost=0.15  # GPT-4 Turbo cost
        )
        db.add(db_lesson)
        
        # Update organization usage
        org.total_lessons_generated += 1
        
        db.commit()
        db.refresh(db_lesson)
        
        return db_lesson
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate lesson plan: {str(e)}")


@app.get("/api/lessons", response_model=List[schemas.LessonPlan])
async def get_lesson_plans(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get user's lesson plans"""
    lessons = db.query(models.LessonPlan).filter(
        models.LessonPlan.user_id == current_user.id
    ).order_by(models.LessonPlan.created_at.desc()).offset(skip).limit(limit).all()
    return lessons


@app.get("/api/lessons/{lesson_id}", response_model=schemas.LessonPlan)
async def get_lesson_plan(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific lesson plan"""
    lesson = db.query(models.LessonPlan).filter(models.LessonPlan.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    
    # Check permissions
    if lesson.user_id != current_user.id and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return lesson


@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson_plan(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a lesson plan"""
    lesson = db.query(models.LessonPlan).filter(models.LessonPlan.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    
    # Check permissions
    if lesson.user_id != current_user.id and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(lesson)
    db.commit()
    return {"message": "Lesson plan deleted successfully"}


# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/admin/organizations", response_model=List[schemas.Organization])
async def list_organizations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all organizations (admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    orgs = db.query(models.Organization).all()
    return orgs


@app.get("/api/admin/stats", response_model=schemas.AdminStats)
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get platform-wide statistics (admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_orgs = db.query(models.Organization).count()
    total_users = db.query(models.User).count()
    total_lessons = db.query(models.LessonPlan).count()
    
    # This month's lessons
    now = datetime.utcnow()
    first_day = datetime(now.year, now.month, 1)
    monthly_lessons = db.query(models.LessonPlan).filter(
        models.LessonPlan.created_at >= first_day
    ).count()
    
    # Calculate total API cost
    total_cost = db.query(models.LessonPlan).with_entities(
        db.func.sum(models.LessonPlan.api_cost)
    ).scalar() or 0
    
    return {
        "total_organizations": total_orgs,
        "total_users": total_users,
        "total_lessons": total_lessons,
        "monthly_lessons": monthly_lessons,
        "total_api_cost": float(total_cost)
    }


# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Edu-SmartAI API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "openai": "configured" if openai.api_key else "not configured"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
