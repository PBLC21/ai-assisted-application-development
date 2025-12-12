"""
TEKS Standards Service
Handles loading and querying Texas Essential Knowledge and Skills standards
"""

import json
import os
from typing import List, Dict, Optional


class TEKSService:
    """Service for managing TEKS standards data"""
    
    def __init__(self):
        """Initialize the service and load TEKS data"""
        self.teks_data: Dict = {}
        self._load_teks_data()
    
    def _load_teks_data(self) -> None:
        """Load TEKS standards from JSON file"""
        try:
            # Get the path to the TEKS JSON file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "teks_standards.json")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                self.teks_data = json.load(f)
            
            print(f"✅ TEKS data loaded successfully from {json_path}")
            print(f"📊 Loaded data for grades: {list(self.teks_data.keys())}")
            
        except FileNotFoundError:
            print(f"❌ Error: TEKS standards file not found at {json_path}")
            self.teks_data = {}
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in TEKS file: {e}")
            self.teks_data = {}
        except Exception as e:
            print(f"❌ Error loading TEKS data: {e}")
            self.teks_data = {}
    
    def get_standards(self, grade: str, subject: str) -> List[Dict]:
        """
        Get TEKS standards for a specific grade and subject
        
        Args:
            grade: Grade level (K, 1, 2, 3, 4, 5, 6, 7, 8)
            subject: Subject name (Mathematics, English Language Arts, Science, Social Studies)
        
        Returns:
            List of TEKS standard dictionaries
        """
        try:
            # Validate grade exists
            if grade not in self.teks_data:
                return []
            
            # Get subject standards
            grade_data = self.teks_data[grade]
            
            # Return standards for subject (empty list if subject doesn't exist)
            return grade_data.get(subject, [])
            
        except Exception as e:
            print(f"❌ Error getting standards for {grade} {subject}: {e}")
            return []
    
    def get_standard_by_code(self, teks_code: str) -> Optional[Dict]:
        """
        Find a specific TEKS standard by its code
        
        Args:
            teks_code: TEKS code (e.g., "4.7(D)", "3.4K")
        
        Returns:
            TEKS standard dictionary or None if not found
        """
        try:
            # Search through all grades and subjects
            for grade, subjects in self.teks_data.items():
                for subject, standards in subjects.items():
                    for standard in standards:
                        if standard.get("code") == teks_code:
                            return standard
            
            return None
            
        except Exception as e:
            print(f"❌ Error searching for TEKS code {teks_code}: {e}")
            return None
    
    def get_available_grades(self) -> List[str]:
        """Get list of available grade levels"""
        return list(self.teks_data.keys())
    
    def get_available_subjects(self, grade: str) -> List[str]:
        """
        Get list of available subjects for a grade
        
        Args:
            grade: Grade level
        
        Returns:
            List of subject names
        """
        if grade in self.teks_data:
            return list(self.teks_data[grade].keys())
        return []
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the TEKS database
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_grades": len(self.teks_data),
            "grades": list(self.teks_data.keys()),
            "subjects_by_grade": {},
            "standards_count_by_grade": {},
            "total_standards": 0
        }
        
        for grade, subjects in self.teks_data.items():
            stats["subjects_by_grade"][grade] = list(subjects.keys())
            
            grade_total = 0
            for subject, standards in subjects.items():
                grade_total += len(standards)
            
            stats["standards_count_by_grade"][grade] = grade_total
            stats["total_standards"] += grade_total
        
        return stats


# Create singleton instance
teks_service = TEKSService()
