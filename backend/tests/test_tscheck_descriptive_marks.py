import io
import uuid


def account_and_document(client):
    suffix = uuid.uuid4().hex[:10]
    reg = client.post('/auth/register', json={'display_name': 'tscheck-descriptive', 'email': f'tscheck-descriptive-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert reg.status_code == 200, reg.text
    filename = f"tscheck-descriptive-{suffix}.txt"
    content = b"StatNex AI descriptive fixture: Photosynthesis converts light energy into chemical energy in plants."
    files = [('files', (filename, io.BytesIO(content), 'text/plain'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()[0]['id']


def test_descriptive_exam_reflects_chosen_marks(client):
    document_id = account_and_document(client)
    response = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'descriptive', 'prompt': '', 'marks': 2})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['action'] == 'descriptive'
    assert body['marks'] == 2
    assert len(body['content'].strip()) > 10

    response_10 = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'descriptive', 'prompt': '', 'marks': 10})
    assert response_10.status_code == 200, response_10.text
    body_10 = response_10.json()
    assert body_10['marks'] == 10
    assert len(body_10['content'].strip()) > 10


def test_descriptive_exam_rejects_missing_document(client):
    suffix = uuid.uuid4().hex[:10]
    reg = client.post('/auth/register', json={'display_name': 'tscheck-descriptive-bad', 'email': f'tscheck-descriptive-bad-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert reg.status_code == 200, reg.text
    response = client.post('/modules/documents/does-not-exist/analyze', json={'action': 'descriptive', 'prompt': '', 'marks': 5})
    assert response.status_code == 404, response.text
