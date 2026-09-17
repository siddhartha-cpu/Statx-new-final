import io
import uuid


def account_and_pdf_document(client):
    suffix = uuid.uuid4().hex[:10]
    reg = client.post('/auth/register', json={'display_name': 'tscheck-assignment', 'email': f'tscheck-assignment-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert reg.status_code == 200, reg.text
    with open('/app/.emergent/fixtures/tscheck-assignment.pdf', 'rb') as fh:
        pdf_bytes = fh.read()
    filename = f"tscheck-assignment-{suffix}.pdf"
    files = [('files', (filename, io.BytesIO(pdf_bytes), 'application/pdf'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()[0]['id']


def test_assignment_generation_reflects_chosen_marks(client):
    document_id = account_and_pdf_document(client)
    response = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'assignment', 'prompt': '', 'marks': 10})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['action'] == 'assignment'
    assert body['marks'] == 10
    assert len(body['content'].strip()) > 10
