import io
import uuid


def account_and_mcq_analysis(client):
    suffix = uuid.uuid4().hex[:10]
    reg = client.post('/auth/register', json={'display_name': 'tscheck-exam-results', 'email': f'tscheck-exam-results-{suffix}@example.com', 'password': 'StrongPass123!'})
    assert reg.status_code == 200, reg.text
    filename = f"tscheck-exam-{suffix}.txt"
    content = b"StatNex AI exam fixture: The mitochondria is the powerhouse of the cell."
    files = [('files', (filename, io.BytesIO(content), 'text/plain'))]
    uploaded = client.post('/modules/documents/upload', files=files)
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()[0]['id']
    mcqs = client.post(f'/modules/documents/{document_id}/analyze', json={'action': 'mcqs', 'prompt': ''})
    assert mcqs.status_code == 200, mcqs.text
    return document_id, mcqs.json()['id']


def test_saved_mcq_result_appears_in_results_list(client):
    document_id, analysis_id = account_and_mcq_analysis(client)
    saved = client.post(f'/modules/documents/{document_id}/exam-results', json={'analysis_id': analysis_id, 'correct': 4, 'total': 5})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body['document_id'] == document_id
    assert body['correct'] == 4
    assert body['total'] == 5
    assert body['percentage'] == 80
    listed = client.get('/modules/results/exams')
    assert listed.status_code == 200, listed.text
    assert any(x['id'] == body['id'] for x in listed.json())


def test_saved_mcq_result_rejects_correct_exceeding_total(client):
    document_id, analysis_id = account_and_mcq_analysis(client)
    saved = client.post(f'/modules/documents/{document_id}/exam-results', json={'analysis_id': analysis_id, 'correct': 9, 'total': 5})
    assert saved.status_code == 422, saved.text
