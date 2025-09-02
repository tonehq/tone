from typing import Dict, Any

def model_to_dict(model) -> Dict[str, Any]:
    """Convert SQLAlchemy model instance to dictionary"""
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}