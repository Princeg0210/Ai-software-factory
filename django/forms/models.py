class ValidationError(Exception):
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
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
