import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-provider-api', 'email': f'tscheck-provider-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text
    return response.json()


def test_provider_status_is_neutral_and_server_only(client):
    account(client)
    providers = client.get('/providers')
    assert providers.status_code == 200, providers.text
    rows = providers.json()
    # Only the neutral StatNex AI service is exposed to the browser - no vendor key fields.
    assert len(rows) == 1, rows
    engine = rows[0]
    assert engine['id'] == 'statx-engine'
    assert engine['configured'] is True
    assert 'api_key' not in engine and 'token' not in engine
    updated = client.patch('/providers/preferences', json={'provider_ids': ['statx-engine'], 'fallback_enabled': True})
    assert updated.status_code == 200, updated.text
    assert updated.json()['provider_ids'] == ['statx-engine']
    gemini = client.get('/providers/gemini/connect')
    assert gemini.status_code == 503, gemini.text
    assert 'not configured' in gemini.text.lower()
