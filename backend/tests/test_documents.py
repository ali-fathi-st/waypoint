"""Uploads: checked by content, size-limited, stored privately, versioned."""

import io
import zipfile

from tests.conftest import contract_fields

URL = "/api/v1/documents"
PDF = b"%PDF-1.7\n" + b"0" * 1000


def docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def upload(client, data=PDF, name="resume.pdf", **form):
    fields = {"document_type": "resume", "title": "New résumé", **form}
    return client.post(URL, data=fields, files={"file": (name, data, "application/octet-stream")})


def test_list_hides_archived_unless_asked(client, demo):
    shown = client.get(URL).json()
    assert all(d["status"] != "archived" for d in shown)
    everything = client.get(URL, params={"include_archived": "true"}).json()
    assert len(everything) == len(demo["documents"])
    assert not [f for f in contract_fields()["document"] if f not in everything[0]]


def test_filter_by_type(client):
    letters = client.get(URL, params={"document_type": "cover_letter"}).json()
    assert letters and all(d["document_type"] == "cover_letter" for d in letters)


def test_upload_pdf_stores_privately_and_counts_versions(client, private_storage):
    response = upload(client)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["version"] == 4, "the demo already has résumé v1-v3"
    assert doc["origin"] == "uploaded" and doc["file_name"] == "resume.pdf" and doc["size_bytes"] == len(PDF)
    assert "storage_key" not in doc and "path" not in str(doc).lower()
    stored = list(private_storage.iterdir())
    assert len(stored) == 1 and stored[0].read_bytes() == PDF
    assert stored[0].name.startswith(doc["id"]), "stored by id, not by your file name"


def test_upload_docx_and_link_a_job(client):
    response = upload(client, docx(), "letter.docx", document_type="cover_letter", related_job_id="job_001")
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["related_job_title"] and doc["version"] == 1


def test_rejects_other_files_even_if_named_pdf(client):
    response = upload(client, b"hello, I am a text file", "sneaky.pdf")
    assert response.status_code == 422


def test_rejects_files_over_5mb(client):
    assert upload(client, b"%PDF-" + b"0" * (5 * 1024 * 1024)).status_code == 422


def test_file_names_are_made_safe(client):
    doc = upload(client, name="../../etc/passwd<>.pdf").json()
    assert "/" not in doc["file_name"] and ".." not in doc["file_name"].split("passwd")[0]


def test_blank_title_is_refused(client):
    assert upload(client, title="   ").status_code == 422


def test_rename_and_archive(client):
    doc = client.patch(f"{URL}/doc_002", json={"title": "Renamed"}).json()
    assert doc["title"] == "Renamed"
    doc = client.patch(f"{URL}/doc_002", json={"status": "archived"}).json()
    assert doc["status"] == "archived" and doc["title"] == "Renamed"
    assert client.patch(f"{URL}/doc_002", json={"title": " "}).status_code == 422
    assert client.patch(f"{URL}/doc_nope", json={"title": "x"}).status_code == 404
