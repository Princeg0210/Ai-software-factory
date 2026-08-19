import os
from celery import Celery
from fsm.orchestrator import FSMOrchestrator
from database import SessionLocal

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "factory_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="tasks.execute_fsm_task", bind=True)
def execute_fsm_task(self, issue_payload, workspace_dir):
    """
    Executes the deterministic FSM pipeline asynchronously in a Celery worker.
    """
    db = SessionLocal()
    try:
        orchestrator = FSMOrchestrator(
            issue_payload=issue_payload,
            workspace_dir=workspace_dir,
            db_session=db,
            use_docker=False
        )
        result = orchestrator.run_to_completion()
        return result
    finally:
        db.close()
