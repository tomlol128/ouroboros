import pytest
from ouroboros.tools.refresh_free_models import refresh_free_models

def test_refresh_free_models():
    success, data = refresh_free_models()
    if not success:
        # In test environment without API key, expect this message
        assert "No working free models found" in data
    else:
        assert 'working_models' in data
        assert len(data['working_models']) > 0
        assert 'timestamp' in data