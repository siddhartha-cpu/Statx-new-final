import io
import uuid


def account(client):
    suffix = uuid.uuid4().hex[:10]
    response = client.post('/auth/register', json={'display_name': 'tscheck-modules-api', 'email': f'tscheck-modules-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert response.status_code == 200, response.text
    return response.json()


def test_document_upload_persists_with_metadata(client):
    account(client)
    filename = f"tscheck-doc-{uuid.uuid4().hex[:8]}.txt"
    files = [('files', (filename, io.BytesIO(b'tscheck sample document content'), 'text/plain'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    item = uploaded.json()[0]
    assert item['file_name'] == filename
    assert item['file_type'] == 'text/plain'
    assert item['file_size'] > 0
    listed = client.get('/modules/documents')
    assert listed.status_code == 200, listed.text
    assert any(x['id'] == item['id'] and x['file_name'] == filename for x in listed.json())


def test_document_upload_rejects_invalid_type(client):
    account(client)
    files = [('files', ('tscheck-bad.exe', io.BytesIO(b'not a real doc'), 'application/x-msdownload'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 415, uploaded.text


def test_multiple_document_upload_in_single_request_persists_both(client):
    account(client)
    suffix = uuid.uuid4().hex[:8]
    name_a = f"tscheck-multi-a-{suffix}.txt"
    name_b = f"tscheck-multi-b-{suffix}.txt"
    files = [
        ('files', (name_a, io.BytesIO(b'tscheck first document content'), 'text/plain')),
        ('files', (name_b, io.BytesIO(b'tscheck second document content'), 'text/plain')),
    ]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    items = uploaded.json()
    assert len(items) == 2
    returned_names = {x['file_name'] for x in items}
    assert returned_names == {name_a, name_b}
    listed = client.get('/modules/documents')
    assert listed.status_code == 200, listed.text
    listed_names = {x['file_name'] for x in listed.json()}
    assert name_a in listed_names and name_b in listed_names


def test_module_item_creation_persists_across_kinds(client):
    account(client)
    for kind in ('competency', 'results', 'assessment'):
        title = f'tscheck-{kind}-{uuid.uuid4().hex[:8]}'
        created = client.post(f'/modules/{kind}', json={'title': title, 'description': 'tscheck description'})
        assert created.status_code == 200, created.text
        item = created.json()
        assert item['title'] == title
        listed = client.get(f'/modules/{kind}')
        assert listed.status_code == 200, listed.text
        assert any(x['id'] == item['id'] for x in listed.json())
