import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool
from docx import Document
from pypdf import PdfReader

from lib.db import db
from lib.providers import ProviderError, route_with_fallback
from lib.security import user_id_from_request
from models import CreateModuleItemRequest, DocumentActionRequest, DocumentAnalysis, ExamResult, ExamResultRequest, ModuleItem

router = APIRouter(prefix="/modules", tags=["modules"])
ALLOWED = {"documents", "competency", "results", "assessment"}
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/statx-uploads"))


def _check(kind: str) -> str:
    if kind not in ALLOWED:
        raise HTTPException(status_code=404, detail="Module not found")
    return kind


def _public(doc: dict) -> ModuleItem:
    return ModuleItem(**{k: doc.get(k) for k in ("id", "kind", "title", "description", "status", "updated_at", "file_name", "file_type", "file_size")})


def _extract_text(path: Path, content_type: str) -> str:
    if content_type in {"text/plain", "text/markdown", "text/csv"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif content_type == "application/pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    else:
        text = ""
    return text.strip()[:120_000]


@router.get("/{kind}", response_model=list[ModuleItem])
async def list_items(kind: str, request: Request):
    _check(kind)
    user_id = user_id_from_request(request)
    docs = await db.module_items.find({"user_id": user_id, "kind": kind}).sort("updated_at", -1).to_list(100)
    return [_public(x) for x in docs]


@router.post("/documents/upload", response_model=list[ModuleItem])
async def upload_documents(request: Request, files: list[UploadFile] = File(...)):
    user_id = user_id_from_request(request)
    allowed_types = {"application/pdf", "text/plain", "text/markdown", "text/csv", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if not files:
        raise HTTPException(status_code=422, detail="Choose at least one document")
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    created: list[ModuleItem] = []
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=415, detail=f"{file.filename or 'File'} is not a supported document")
        item_id = str(uuid.uuid4())
        safe_name = Path(file.filename or "uploaded-document").name
        storage_path = user_dir / item_id
        size = 0
        with storage_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                target.write(chunk)
                size += len(chunk)
        now = datetime.now(timezone.utc)
        doc = {"id": item_id, "user_id": user_id, "kind": "documents", "title": safe_name, "description": "Uploaded source material", "status": "active", "updated_at": now, "file_name": safe_name, "file_type": file.content_type, "file_size": size, "storage_path": str(storage_path)}
        await db.module_items.insert_one(doc)
        created.append(_public(doc))
    return created


@router.get("/documents/{document_id}/analyses", response_model=list[DocumentAnalysis])
async def list_document_analyses(document_id: str, request: Request):
    user_id = user_id_from_request(request)
    if not await db.module_items.find_one({"id": document_id, "user_id": user_id, "kind": "documents"}):
        raise HTTPException(status_code=404, detail="Document not found")
    docs = await db.document_analyses.find({"document_id": document_id, "user_id": user_id}).sort("created_at", -1).to_list(50)
    return [DocumentAnalysis(id=x["id"], document_id=x["document_id"], action=x["action"], content=x["content"], created_at=x["created_at"], prompt=x.get("prompt"), marks=x.get("marks")) for x in docs]


@router.post("/documents/{document_id}/analyze", response_model=DocumentAnalysis)
async def analyze_document(document_id: str, payload: DocumentActionRequest, request: Request):
    user_id = user_id_from_request(request)
    document = await db.module_items.find_one({"id": document_id, "user_id": user_id, "kind": "documents"})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(document.get("storage_path", ""))
    if not path.is_file():
        raise HTTPException(status_code=409, detail="The uploaded document file is unavailable")
    text = await run_in_threadpool(_extract_text, path, document.get("file_type", ""))
    if not text:
        raise HTTPException(status_code=422, detail="No readable text was found in this document")
    prompts = {
        "summary": "Summarize this document clearly. Use short sections and preserve the most important facts.",
        "notes": "Create concise study notes from this document with headings and bullet points.",
        "flashcards": "Create 8 useful flashcards. Format each as Q: question followed by A: answer.",
        "mcqs": "Create 6 multiple-choice questions from this document. Use this strict format for every item: Question 1: text, then separate lines A) option, B) option, C) option, D) option, Correct: A, Why: a clear one-sentence explanation grounded in the document.",
        "descriptive": f"Create 6 descriptive exam questions from this document. Each question is worth {payload.marks or 5} marks. After the questions, provide a concise marking guide for each answer.",
        "assignment": f"Create a practical homework assignment from this document with clear instructions, deliverables, and a marking guide. Use {payload.marks or 5}-mark questions where appropriate.",
        "ask": payload.prompt.strip() or "Explain the most important idea in this document.",
    }
    message = f"{prompts[payload.action]}\n\nDocument: {document['title']}\n\n{text}"
    try:
        result, _ = await route_with_fallback(user_id, [{"role": "user", "content": message}], [], f"document:{document_id}:{payload.action}")
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail={"code": "ai_unavailable", "message": exc.message}) from exc
    now = datetime.now(timezone.utc)
    analysis = {"id": str(uuid.uuid4()), "user_id": user_id, "document_id": document_id, "action": payload.action, "content": result.text, "created_at": now, "prompt": payload.prompt.strip() if payload.action == "ask" else None, "marks": payload.marks}
    await db.document_analyses.insert_one(analysis)
    return DocumentAnalysis(id=analysis["id"], document_id=document_id, action=payload.action, content=result.text, created_at=now, prompt=analysis["prompt"], marks=payload.marks)


@router.post("/documents/{document_id}/exam-results", response_model=ExamResult)
async def save_exam_result(document_id: str, payload: ExamResultRequest, request: Request):
    user_id = user_id_from_request(request)
    document = await db.module_items.find_one({"id": document_id, "user_id": user_id, "kind": "documents"})
    analysis = await db.document_analyses.find_one({"id": payload.analysis_id, "document_id": document_id, "user_id": user_id})
    if not document or not analysis or analysis.get("action") != "mcqs":
        raise HTTPException(status_code=404, detail="Exam not found")
    if payload.correct > payload.total:
        raise HTTPException(status_code=422, detail="Correct answers cannot exceed total questions")
    now = datetime.now(timezone.utc)
    percentage = round(payload.correct / payload.total * 100)
    feedback = "Strong result. Revisit the explanations for any missed questions and try a new set to reinforce recall." if percentage >= 70 else "Keep practicing. Review the document sections behind the missed questions, then retry with fresh MCQs."
    result = {"id": str(uuid.uuid4()), "user_id": user_id, "document_id": document_id, "document_title": document["title"], "analysis_id": payload.analysis_id, "kind": "mcqs", "correct": payload.correct, "total": payload.total, "percentage": percentage, "submitted_at": now, "feedback": feedback}
    await db.exam_results.update_one({"user_id": user_id, "analysis_id": payload.analysis_id}, {"$set": result}, upsert=True)
    return ExamResult(**{key: result.get(key) for key in ("id", "document_id", "document_title", "analysis_id", "kind", "correct", "total", "percentage", "submitted_at", "feedback")})


@router.post("/assignments/{analysis_id}/submit", response_model=ExamResult)
async def submit_assignment(analysis_id: str, request: Request, file: UploadFile = File(...)):
    user_id = user_id_from_request(request)
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Submit the completed assignment as a PDF")
    assignment = await db.document_analyses.find_one({"id": analysis_id, "user_id": user_id, "action": "assignment"})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    document = await db.module_items.find_one({"id": assignment["document_id"], "user_id": user_id})
    submission_id = str(uuid.uuid4())
    folder = UPLOAD_DIR / user_id / "submissions"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / submission_id
    with path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            target.write(chunk)
    answer_text = await run_in_threadpool(_extract_text, path, "application/pdf")
    if not answer_text:
        raise HTTPException(status_code=422, detail="No readable answers were found in the submitted PDF")
    grading_prompt = f"Grade this completed assignment against the assignment and marking guide. Return exactly: Score: N/100, then Feedback: concise strengths, then How to improve: specific next steps. Be fair and evidence-based.\n\nASSIGNMENT:\n{assignment['content']}\n\nSTUDENT SUBMISSION:\n{answer_text}"
    try:
        result, _ = await route_with_fallback(user_id, [{"role": "user", "content": grading_prompt}], [], f"assignment-grade:{analysis_id}:{submission_id}")
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail={"code": "ai_unavailable", "message": exc.message}) from exc
    score_match = re.search(r"Score\s*:\s*(\d{1,3})\s*/\s*100", result.text, re.IGNORECASE)
    if not score_match:
        raise HTTPException(status_code=502, detail="StatNex AI could not produce a valid assignment score")
    score = max(0, min(100, int(score_match.group(1))))
    now = datetime.now(timezone.utc)
    exam_result = {"id": str(uuid.uuid4()), "user_id": user_id, "document_id": assignment["document_id"], "document_title": (document or {}).get("title", "Assignment"), "analysis_id": analysis_id, "kind": "assignment", "correct": score, "total": 100, "percentage": score, "submitted_at": now, "feedback": result.text, "submission_path": str(path)}
    await db.exam_results.insert_one(exam_result)
    return ExamResult(**{key: exam_result.get(key) for key in ("id", "document_id", "document_title", "analysis_id", "kind", "correct", "total", "percentage", "submitted_at", "feedback")})


@router.get("/results/exams", response_model=list[ExamResult])
async def list_exam_results(request: Request):
    user_id = user_id_from_request(request)
    docs = await db.exam_results.find({"user_id": user_id}).sort("submitted_at", -1).to_list(100)
    return [ExamResult(**{key: row.get(key) for key in ("id", "document_id", "document_title", "analysis_id", "kind", "correct", "total", "percentage", "submitted_at", "feedback")}) for row in docs]


@router.post("/{kind}", response_model=ModuleItem)
async def create_item(kind: str, payload: CreateModuleItemRequest, request: Request):
    _check(kind)
    user_id = user_id_from_request(request)
    doc = {"id": str(uuid.uuid4()), "user_id": user_id, "kind": kind, "title": payload.title, "description": payload.description, "status": "active", "updated_at": datetime.now(timezone.utc)}
    await db.module_items.insert_one(doc)
    return _public(doc)
