import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-provider-api', 'email': f'tscheck-provider-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text
    return response.json()


def test_provider_selection_is_separate_from_connection(client):
    account(client)
    providers = client.get('/providers')
    assert providers.status_code == 200, providers.text
    rows = providers.json()
    assert any(row['id'] == 'gemini' and row['status'] != 'connected' for row in rows)
    updated = client.patch('/providers/preferences', json={'provider_ids': ['openai'], 'fallback_enabled': True})
    assert updated.status_code == 200, updated.text
    assert updated.json()['provider_ids'] == ['openai']
    gemini = client.get('/providers/gemini/connect')
    assert gemini.status_code == 503, gemini.text
    assert 'not configured' in gemini.text.lower()
