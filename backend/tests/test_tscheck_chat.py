import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-chat-api', 'email': f'tscheck-chat-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text


def test_chat_persists_user_and_demo_assistant(client):
    account(client)
    created = client.post('/conversations', json={'title': 'tscheck-chat-thread'})
    assert created.status_code == 200, created.text
    conversation_id = created.json()['id']
    sent = client.post(f'/conversations/{conversation_id}/messages', json={'content': 'tscheck api prompt', 'provider_ids': ['demo'], 'search_mode': 'ai-only'})
    assert sent.status_code == 200, sent.text
    assert sent.json()['message']['provider_id'] == 'demo'
    detail = client.get(f'/conversations/{conversation_id}')
    assert detail.status_code == 200, detail.text
    messages = detail.json()['messages']
    assert any(m['role'] == 'user' and m['content'] == 'tscheck api prompt' for m in messages)
    assert any(m['role'] == 'assistant' and m['provider_id'] == 'demo' for m in messages)
