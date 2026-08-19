import os
import json
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from fsm.orchestrator import FSMOrchestrator
from fsm.states import FSMState
from fsm.ledger import StateLedger

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_fsm_orchestrator_end_to_end(test_db):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Create simulated repository structure matching django-13933
        django_forms_dir = os.path.join(tmp_dir, "django", "forms")
        tests_dir = os.path.join(tmp_dir, "tests")
        os.makedirs(django_forms_dir, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)

        models_file = os.path.join(django_forms_dir, "models.py")
        original_models_code = """class ValidationError(Exception):
    def __init__(self, message, code=None, params=None):
        self.message = message
        self.code = code
        self.params = params

class DummyModel:
    class DoesNotExist(Exception):
        pass

class DummyQuerySet:
    def __init__(self):
        self.model = DummyModel

    def get(self, pk):
        raise self.model.DoesNotExist("Invalid PK")

class ModelChoiceField:
    def __init__(self, queryset=None, error_messages=None):
        self.queryset = queryset or DummyQuerySet()
        self.error_messages = error_messages or {'invalid_choice': 'Invalid choice'}

    def to_python(self, value):
        if value in (None, ''):
            return None
        try:
            return self.queryset.get(pk=value)
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
"""
        with open(models_file, "w") as f:
            f.write(original_models_code)

        test_file = os.path.join(tests_dir, "test_model_fields.py")
        test_code = """import pytest
from django.forms.models import ModelChoiceField, ValidationError

def test_model_choice_field():
    field = ModelChoiceField()
    with pytest.raises(ValidationError):
        field.to_python("999")
"""
        with open(test_file, "w") as f:
            f.write(test_code)

        # 2. Ingest mock payload
        with open("mock-payload.json", "r") as f:
            payload = json.load(f)

        orchestrator = FSMOrchestrator(
            issue_payload=payload,
            workspace_dir=tmp_dir,
            db_session=test_db,
            use_docker=False
        )

        # 3. Run FSM to completion
        result = orchestrator.run_to_completion()

        assert result["issue_id"] == "django-13933"
        assert result["final_state"] in [FSMState.MERGE.value, FSMState.TERMINAL_SUCCESS.value, FSMState.HUMAN_REVIEW.value]
        
        # 4. Verify Database Ledger Entries
        ledger = StateLedger(db=test_db)
        history = ledger.get_history("django-13933")
        
        state_names = [h["state"] for h in history]
        assert FSMState.INIT.value in state_names
        assert FSMState.LOCALIZATION.value in state_names
        assert FSMState.PLANNING.value in state_names
        assert FSMState.REPAIR.value in state_names
        assert FSMState.VERIFICATION.value in state_names

        # 5. Verify the code on disk was successfully modified
        with open(models_file, "r") as f:
            updated_content = f.read()
        assert "params={'value': value}" in updated_content
