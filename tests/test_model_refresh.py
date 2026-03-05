import asyncio
import pytest
import os
import json
from ouroboros.tools.refresh_free_models import refresh_free_models

def test_refresh_free_models():
    result = asyncio.run(refresh_free_models())
    assert 'status' in result
    if result['status'] == 'success':
        assert 'models' in result
        assert isinstance(result['models'], list)
        if len(result['models']) > 0:
            assert 'id' in result['models'][0]
            assert 'context_window' in result['models'][0]

def test_api_endpoint_creation():
    # Verify model list is written to API endpoint
    result = asyncio.run(refresh_free_models())
    assert result['status'] == 'success'
    
    api_path = os.path.join(os.getenv('REPO_DIR', '/app'), 'webapp', 'api', 'models')
    assert os.path.exists(api_path)
    with open(api_path, 'r') as f:
        data = json.load(f)
        assert 'models' in data
        assert isinstance(data['models'], list)