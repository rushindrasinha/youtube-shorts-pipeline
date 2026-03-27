from uuid import UUID
from sqlalchemy.orm import Session
from saas.models.audit import AuditLog

def log_action(db: Session, action: str, user_id: UUID = None, team_id: UUID = None, resource_type: str = None, resource_id: UUID = None, details: dict = None, ip_address: str = None):
    db.add(AuditLog(user_id=user_id, team_id=team_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details or {}, ip_address=ip_address))
    db.commit()
