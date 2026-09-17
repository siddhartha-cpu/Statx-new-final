import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-auth-api', 'email': f'tscheck-auth-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text
    return response.json()


def test_register_login_and_protected_me(client):
    user = account(client)
    assert user['email'].startswith('tscheck-auth-')
    me = client.get('/auth/me')
    assert me.status_code == 200, me.text
    assert me.json()['id'] == user['id']
    client.post('/auth/logout')
    denied = client.get('/auth/me')
    assert denied.status_code == 401, denied.text
    login = client.post('/auth/login', json={'email': user['email'], 'password': 'StrongPass123!'})
    assert login.status_code == 200, login.text
    assert login.json()['id'] == user['id']
