"""
Résumé and cover-letter versions. Uploads are checked by content (real PDF or
.docx, at most 5 MB), stored privately (app/services/storage.py), and only
their metadata is ever returned.
"""

import re

import psycopg
from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.db import get_db
from app.rows import SELECT_DOCUMENT, row_to_document
from app.schemas import Document, DocumentType, DocumentUpdate
from app.services import storage
from app.util import invalid, new_id, not_found, utc_now

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get(db, doc_id: str) -> Document:
    row = db.execute(SELECT_DOCUMENT + " WHERE d.id = %s", (doc_id,)).fetchone()
    if row is None:
        raise not_found("Document")
    return row_to_document(row)


def safe_file_name(name: str | None) -> str:
    """Keep just the base name, without paths or odd characters."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^\w.\- ()]+", "_", base).strip(" .") or "upload"
    return base[-120:]


@router.get("", response_model=list[Document])
def list_documents(
    document_type: DocumentType | None = None,
    include_archived: bool = False,
    db: psycopg.Connection = Depends(get_db),
) -> list[Document]:
    where, params = [], []
    if document_type:
        where.append("d.document_type = %s")
        params.append(document_type)
    if not include_archived:
        where.append("d.status <> 'archived'")
    sql = SELECT_DOCUMENT + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY d.document_type, d.version DESC, d.created_at DESC"
    return [row_to_document(r) for r in db.execute(sql, params).fetchall()]


@router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: DocumentType = Form(...),
    title: str = Form(..., max_length=200),
    related_job_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: psycopg.Connection = Depends(get_db),
) -> Document:
    if not title.strip():
        raise invalid("Give this version a name.", "title")
    data = await file.read(storage.MAX_BYTES + 1)
    if len(data) > storage.MAX_BYTES:
        raise invalid("Files can be up to 5 MB.", "file")
    content_type = storage.detect_type(data)
    if content_type is None:
        raise invalid("Upload a PDF or Word (.docx) file.", "file")
    if related_job_id:
        if db.execute("SELECT 1 FROM jobs WHERE id = %s", (related_job_id,)).fetchone() is None:
            raise invalid("That job doesn't exist.", "related_job_id")
    else:
        related_job_id = None

    doc_id = new_id("doc")
    key = doc_id + (".pdf" if content_type == storage.PDF else ".docx")
    # Versions count per type and job (résumé v1, v2...; each job's cover letter v1, v2...).
    # The lock makes uploads take turns, so two never get the same number.
    db.execute("SELECT pg_advisory_xact_lock(hashtext('documents:' || %s))", (document_type,))
    version = db.execute(
        "SELECT coalesce(max(version), 0) + 1 AS v FROM documents "
        "WHERE document_type = %s AND related_job_id IS NOT DISTINCT FROM %s",
        (document_type, related_job_id),
    ).fetchone()["v"]
    now = utc_now()
    db.execute(
        """
        INSERT INTO documents (id, document_type, title, version, status, origin, related_job_id,
                               file_name, size_bytes, content_type, storage_key, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'ready', 'uploaded', %s, %s, %s, %s, %s, %s, %s)
        """,
        (doc_id, document_type, title.strip(), version, related_job_id, safe_file_name(file.filename),
         len(data), content_type, key, now, now),
    )  # fmt: skip
    storage.save(key, data)  # after the INSERT succeeds; if saving fails, the transaction rolls back
    return get(db, doc_id)


@router.patch("/{doc_id}", response_model=Document)
def update_document(doc_id: str, body: DocumentUpdate, db: psycopg.Connection = Depends(get_db)) -> Document:
    get(db, doc_id)
    sent = body.model_fields_set
    if "title" in sent and body.title is not None:
        if not body.title.strip():
            raise invalid("Give this version a name.", "title")
        db.execute("UPDATE documents SET title = %s WHERE id = %s", (body.title.strip(), doc_id))
    if "status" in sent and body.status is not None:
        db.execute("UPDATE documents SET status = %s WHERE id = %s", (body.status, doc_id))
    db.execute("UPDATE documents SET updated_at = %s WHERE id = %s", (utc_now(), doc_id))
    return get(db, doc_id)
