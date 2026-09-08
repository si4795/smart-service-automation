"""
Database interface proxy for SmartServe.
Routes all persistence queries directly to the SQLite relational database (smartserve.db).
"""
from database import db, CATEGORIES, STATUS_FLOW, CATEGORY_ALIASES, CATEGORY_SLUGS, Database

__all__ = ["db", "CATEGORIES", "STATUS_FLOW", "CATEGORY_ALIASES", "CATEGORY_SLUGS", "Database"]
