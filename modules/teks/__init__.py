"""
TEKS Standards Module
Provides API endpoints for querying Texas Essential Knowledge and Skills standards
"""

from .router import router
from .service import teks_service

__all__ = ["router", "teks_service"]
