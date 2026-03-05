import pytest
from ouroboros.tools.refresh_free_models import refresh_free_models

def test_refresh_free_models():
    result = refresh_free_models()
    assert 'working_models' in result
    assert len(result['working_models']) > 0
    assert 'timestamp' in result