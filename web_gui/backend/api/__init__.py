"""API module for AgenticSys Web GUI"""

from .routes import router
from .models import *

__all__ = ["router"]