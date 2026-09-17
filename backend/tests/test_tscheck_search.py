import uuid


def test_web_search_without_credential_is_not_claimed_success(client):
    suffix = uuid.uuid4().hex[:10]
    registered = client.post('/auth/register', json={'display_name': 'tscheck-search-api', 'email': f'tscheck-search-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert registered.status_code == 200, registered.text
    created = client.post('/conversations', json={'title': 'tscheck-search-thread'})
    assert created.status_code == 200, created.text
    response = client.post(f"/conversations/{created.json()['id']}/messages", json={'content': 'tscheck current web query', 'provider_ids': [], 'search_mode': 'web'})
    assert response.status_code == 503, response.text
    assert 'search_unavailable' in response.text
