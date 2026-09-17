import uuid


def test_unauthenticated_protected_data_rejected(client):
    response = client.get('/conversations')
    assert response.status_code == 401, response.text
    response = client.get('/providers')
    assert response.status_code == 401, response.text
    suffix = uuid.uuid4().hex[:10]
    registered = client.post('/auth/register', json={'display_name': 'tscheck-protected-api', 'email': f'tscheck-protected-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert registered.status_code == 200, registered.text
    client.post('/auth/logout')
    assert client.get('/auth/me').status_code == 401
