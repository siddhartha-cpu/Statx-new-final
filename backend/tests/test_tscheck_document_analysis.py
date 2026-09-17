import io
import uuid


def account_and_document(client, content=b"StatNex AI tscheck reference: The mitochondria is the powerhouse of the cell."):
    suffix = uuid.uuid4().hex[:10]
    reg = client.post('/auth/register', json={'display_name': 'tscheck-analysis-api', 'email': f'tscheck-analysis-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert reg.status_code == 200, reg.text
    filename = f"tscheck-analysis-{suffix}.txt"
    files = [('files', (filename, io.BytesIO(content), 'text/plain'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()[0]['id']


def test_summarize_document_returns_grounded_result(client):
    document_id = account_and_document(client)
    response = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'summary', 'prompt': ''})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['action'] == 'summary'
    assert isinstance(body['content'], str) and len(body['content'].strip()) > 10
    listed = client.get(f'/modules/documents/{document_id}/analyses')
    assert listed.status_code == 200, listed.text
    assert any(x['id'] == body['id'] and x['action'] == 'summary' for x in listed.json())


def test_ask_document_returns_grounded_answer(client):
    document_id = account_and_document(client)
    question = "What is the mitochondria described as in this document?"
    response = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'ask', 'prompt': question})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['action'] == 'ask'
    assert body['prompt'] == question
    assert isinstance(body['content'], str) and len(body['content'].strip()) > 5


def test_flashcards_and_mcqs_generate_content(client):
    document_id = account_and_document(client)
    flashcards = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'flashcards', 'prompt': ''})
    assert flashcards.status_code == 200, flashcards.text
    assert len(flashcards.json()['content'].strip()) > 10
    mcqs = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'mcqs', 'prompt': ''})
    assert mcqs.status_code == 200, mcqs.text
    assert len(mcqs.json()['content'].strip()) > 10
