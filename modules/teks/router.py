"""
TEKS Standards API Router
Endpoints for querying Texas Essential Knowledge and Skills standards
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict
from .service import teks_service

# Create router
router = APIRouter(
    prefix="/api/teks",
    tags=["TEKS Standards"]
)


@router.get("/grades")
async def get_grades() -> Dict:
    """
    Get list of available grade levels
    
    Returns:
        Dictionary with available grades
    """
    grades = teks_service.get_available_grades()
    return {
        "grades": grades,
        "count": len(grades)
    }


@router.get("/{grade}/{subject}")
async def get_standards(grade: str, subject: str) -> Dict:
    """
    Get TEKS standards for a specific grade and subject
    
    Args:
        grade: Grade level (K, 1, 2, 3, 4, 5, 6, 7, 8)
        subject: Subject name (Mathematics, English Language Arts, Science, Social Studies)
    
    Returns:
        Dictionary with TEKS standards
    """
    # Validate grade
    available_grades = teks_service.get_available_grades()
    if grade not in available_grades:
        raise HTTPException(
            status_code=404,
            detail=f"Grade '{grade}' not found. Available grades: {', '.join(available_grades)}"
        )
    
    # Validate subject
    available_subjects = teks_service.get_available_subjects(grade)
    if subject not in available_subjects:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{subject}' not found for grade {grade}. Available subjects: {', '.join(available_subjects)}"
        )
    
    # Get standards
    standards = teks_service.get_standards(grade, subject)
    
    return {
        "grade": grade,
        "subject": subject,
        "standards": standards,
        "count": len(standards)
    }


@router.get("/{grade}/subjects")
async def get_subjects(grade: str) -> Dict:
    """
    Get available subjects for a specific grade
    
    Args:
        grade: Grade level
    
    Returns:
        Dictionary with available subjects
    """
    # Validate grade
    available_grades = teks_service.get_available_grades()
    if grade not in available_grades:
        raise HTTPException(
            status_code=404,
            detail=f"Grade '{grade}' not found. Available grades: {', '.join(available_grades)}"
        )
    
    subjects = teks_service.get_available_subjects(grade)
    
    return {
        "grade": grade,
        "subjects": subjects,
        "count": len(subjects)
    }


@router.get("/code/{teks_code}")
async def get_standard_by_code(teks_code: str) -> Dict:
    """
    Get a specific TEKS standard by its code
    
    Args:
        teks_code: TEKS code (e.g., "4.7(D)", "3.4K")
    
    Returns:
        TEKS standard details
    """
    standard = teks_service.get_standard_by_code(teks_code)
    
    if not standard:
        raise HTTPException(
            status_code=404,
            detail=f"TEKS standard '{teks_code}' not found"
        )
    
    return {
        "code": teks_code,
        "standard": standard
    }


@router.get("/stats")
async def get_statistics() -> Dict:
    """
    Get statistics about the TEKS database
    
    Returns:
        Dictionary with database statistics
    """
    return teks_service.get_statistics()
