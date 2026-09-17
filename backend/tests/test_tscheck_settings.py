import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-settings-api', 'email': f'tscheck-settings-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text
    return response.json()


def test_fallback_preference_persists_after_toggle(client):
    account(client)
    current = client.get('/providers/preferences')
    assert current.status_code == 200, current.text
    original = current.json()['fallback_enabled']
    toggled = client.patch('/providers/preferences', json={'provider_ids': [], 'fallback_enabled': not original})
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()['fallback_enabled'] == (not original)
    refetched = client.get('/providers/preferences')
    assert refetched.status_code == 200, refetched.text
    assert refetched.json()['fallback_enabled'] == (not original)


def test_account_identity_exposed_without_secrets(client):
    user = account(client)
    me = client.get('/auth/me')
    assert me.status_code == 200, me.text
    body = me.json()
    assert body['email'] == user['email']
    lowered = me.text.lower()
    for forbidden in ('password', 'api_key', 'access_token', 'refresh_token', 'secret'):
        assert forbidden not in lowered, f"{forbidden} leaked in /auth/me response"
