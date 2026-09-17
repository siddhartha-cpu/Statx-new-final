import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-chat-api', 'email': f'tscheck-chat-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text


def test_chat_persists_user_and_statx_engine_assistant(client):
    account(client)
    created = client.post('/conversations', json={'title': 'tscheck-chat-thread'})
    assert created.status_code == 200, created.text
    conversation_id = created.json()['id']
    sent = client.post(f'/conversations/{conversation_id}/messages', json={'content': 'tscheck api prompt', 'provider_ids': [], 'search_mode': 'ai-only'})
    assert sent.status_code == 200, sent.text
    assert sent.json()['message']['provider_id'] == 'statx-engine'
    assert len(sent.json()['message']['content']) > 0
    detail = client.get(f'/conversations/{conversation_id}')
    assert detail.status_code == 200, detail.text
    messages = detail.json()['messages']
    assert any(m['role'] == 'user' and m['content'] == 'tscheck api prompt' for m in messages)
    assert any(m['role'] == 'assistant' and m['provider_id'] == 'statx-engine' for m in messages)


def test_chat_conversation_context_and_isolation(client):
    account(client)
    convo_a = client.post('/conversations', json={'title': 'New conversation'}).json()
    first = client.post(f"/conversations/{convo_a['id']}/messages", json={'content': 'My name is Alex.', 'provider_ids': [], 'search_mode': 'ai-only'})
    assert first.status_code == 200, first.text
    follow_up = client.post(f"/conversations/{convo_a['id']}/messages", json={'content': 'What is my name?', 'provider_ids': [], 'search_mode': 'ai-only'})
    assert follow_up.status_code == 200, follow_up.text
    assert 'alex' in follow_up.json()['message']['content'].lower()
    convo_b = client.post('/conversations', json={'title': 'New conversation'}).json()
    isolated = client.post(f"/conversations/{convo_b['id']}/messages", json={'content': 'What is my name?', 'provider_ids': [], 'search_mode': 'ai-only'})
    assert isolated.status_code == 200, isolated.text
    assert 'alex' not in isolated.json()['message']['content'].lower()
