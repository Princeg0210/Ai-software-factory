import uuid
import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import FSMStateLedger
from database import SessionLocal

class StateLedger:
    def __init__(self, db: Optional[Session] = None):
        self._db = db

    def _get_session(self) -> Session:
        if self._db:
            return self._db
        return SessionLocal()

    def log_state(
        self, 
        issue_id: str, 
        state_name: str, 
        retry_count: int = 0, 
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Atomically records a transition in the immutable state ledger.
        """
        session = self._get_session()
        close_session = (self._db is None)

        try:
            entry = FSMStateLedger(
                state_id=str(uuid.uuid4()),
                issue_id=issue_id,
                state_name=state_name,
                retry_count=retry_count,
                payload=payload or {},
                updated_at=datetime.datetime.utcnow()
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)

            print(f"[Ledger] TRANSITION -> Issue {issue_id}: State is '{state_name}' (Retry: {retry_count})")
            return {
                "state_id": entry.state_id,
                "issue_id": entry.issue_id,
                "state_name": entry.state_name,
                "retry_count": entry.retry_count,
                "payload": entry.payload,
                "updated_at": entry.updated_at.isoformat()
            }
        except Exception as e:
            session.rollback()
            print(f"[Ledger Error] Failed to log state transition: {e}")
            raise e
        finally:
            if close_session:
                session.close()

    def get_history(self, issue_id: str):
        session = self._get_session()
        close_session = (self._db is None)
        try:
            records = session.query(FSMStateLedger).filter(
                FSMStateLedger.issue_id == issue_id
            ).order_by(FSMStateLedger.updated_at.asc()).all()
            
            return [
                {
                    "state": r.state_name,
                    "retry_count": r.retry_count,
                    "payload": r.payload,
                    "timestamp": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in records
            ]
        finally:
            if close_session:
                session.close()
