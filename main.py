import os
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db, init_db
from models import Issue, FSMStateLedger, Patch, HumanReview
from fsm.orchestrator import FSMOrchestrator
from fsm.ledger import StateLedger
from fsm.states import FSMState

# Initialize database tables
init_db()

app = FastAPI(
    title="AI Software Factory API",
    description="FSM-orchestrated, verification-first automated code repair engine.",
    version="1.0.0"
)

# Ensure static folder exists and mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Request Models
class IssueIngestionRequest(BaseModel):
    issue_id: Optional[str] = None
    repository: Dict[str, Any]
    issue: Dict[str, Any]
    verification_settings: Optional[Dict[str, Any]] = None

class HumanReviewRequest(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    reviewer_name: Optional[str] = "Admin"
    comments: Optional[str] = ""

# In-memory tracking for active orchestrators
active_orchestrators: Dict[str, FSMOrchestrator] = {}

def run_fsm_background(payload: Dict[str, Any], workspace_dir: str, issue_id: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        orch = FSMOrchestrator(
            issue_payload=payload,
            workspace_dir=workspace_dir,
            db_session=db
        )
        active_orchestrators[issue_id] = orch
        orch.run_to_completion()
    finally:
        db.close()

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI Software Factory API is running. Access /docs for API schema."}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-software-factory", "version": "1.0.0"}

@app.post("/api/v1/factory/issues", status_code=202)
def ingest_issue(
    request: IssueIngestionRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    issue_id = request.issue_id or str(uuid.uuid4())
    payload = request.model_dump()
    payload["issue_id"] = issue_id

    # Check if issue already exists
    existing_issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
    if not existing_issue:
        new_issue = Issue(
            issue_id=issue_id,
            repo_url=request.repository.get("url", "unknown"),
            issue_title=request.issue.get("title", "Untitled Issue"),
            issue_description=request.issue.get("description", "")
        )
        db.add(new_issue)
        db.commit()

    workspace_dir = os.getenv("WORKSPACE_DIR", "./workspace_repo")
    os.makedirs(workspace_dir, exist_ok=True)

    # Initialize ledger in database
    ledger = StateLedger(db=db)
    ledger.log_state(issue_id, FSMState.INIT.value, retry_count=0, payload=payload)

    # Trigger background FSM runner
    background_tasks.add_task(run_fsm_background, payload, workspace_dir, issue_id)

    return {
        "issue_id": issue_id,
        "status": FSMState.INIT.value,
        "message": "Orchestrator initialized state machine."
    }

@app.get("/api/v1/factory/issues/{issue_id}/status")
def get_issue_status(issue_id: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    ledger = StateLedger(db=db)
    history = ledger.get_history(issue_id)
    current_state = history[-1]["state"] if history else "UNKNOWN"
    retry_count = history[-1]["retry_count"] if history else 0

    return {
        "issue_id": issue_id,
        "current_state": current_state,
        "retry_count": retry_count,
        "history": history
    }

@app.post("/api/v1/factory/issues/{issue_id}/review")
def submit_human_review(
    issue_id: str,
    review: HumanReviewRequest,
    db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.issue_id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    orch = active_orchestrators.get(issue_id)
    if not orch:
        orch = FSMOrchestrator(
            issue_payload={"issue_id": issue_id},
            workspace_dir=os.getenv("WORKSPACE_DIR", "./workspace_repo"),
            db_session=db
        )
        active_orchestrators[issue_id] = orch

    result = orch.process_human_decision(
        decision=review.decision,
        reviewer=review.reviewer_name or "Admin",
        comments=review.comments or ""
    )

    db_review = HumanReview(
        review_id=str(uuid.uuid4()),
        issue_id=issue_id,
        reviewer_name=review.reviewer_name,
        decision=review.decision,
        comments=review.comments
    )
    db.add(db_review)
    db.commit()

    return {
        "issue_id": issue_id,
        "decision": review.decision,
        "new_state": result["state"]
    }

@app.get("/api/v1/factory/issues/{issue_id}/diff")
def get_issue_diff(issue_id: str, db: Session = Depends(get_db)):
    orch = active_orchestrators.get(issue_id)
    if orch and orch.current_patch:
        return {
            "issue_id": issue_id,
            "patch": orch.current_patch.get("patch"),
            "rri_report": orch.rri_report,
            "validation_report": orch.validation_report,
            "mutation_report": orch.mutation_report
        }
    
    ledger = StateLedger(db=db)
    history = ledger.get_history(issue_id)

    patch = None
    rri_report = None
    validation_report = None
    mutation_report = None

    for entry in history:
        p = entry.get("payload") or {}
        if "patch" in p:
            patch = p["patch"]
        if "rri" in p:
            rri_report = p["rri"]
        if "validation_report" in p:
            validation_report = p["validation_report"]
        if "mutation_report" in p:
            mutation_report = p["mutation_report"]

    return {
        "issue_id": issue_id,
        "patch": patch,
        "rri_report": rri_report,
        "validation_report": validation_report,
        "mutation_report": mutation_report,
        "history": history
    }
