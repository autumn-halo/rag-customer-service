"""知识库管理接口测试：权限、上传入库、列表、重解析、删除、分块预览。"""
import time

import pytest

from app.services import ingestion
from tests.fakes.fake_embeddings import FakeEmbeddings

TXT_CONTENT = "退货需在签收后 7 天内发起申请，逾期不予受理。"


@pytest.fixture()
def fake_ingestion(chroma_mem, monkeypatch):
    """入库用假向量化：零 API 消耗（向量库为内存版 Chroma）。"""
    monkeypatch.setattr(ingestion, "get_embeddings", lambda: FakeEmbeddings())


def _wait_status(client, headers, doc_id, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = client.get(f"/api/documents/{doc_id}", headers=headers).json()
        if doc["status"] in ("success", "failed"):
            return doc
        time.sleep(0.1)
    raise AssertionError(f"文档 {doc_id} 在 {timeout}s 内未完成入库")


def _upload_txt(client, headers, filename="退货政策.txt", content=TXT_CONTENT):
    resp = client.post(
        "/api/documents/upload",
        files=[("files", (filename, content.encode("utf-8"), "text/plain"))],
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()[0]


def test_normal_user_forbidden(client, auth_headers):
    headers = auth_headers("alice")
    assert client.get("/api/documents", headers=headers).status_code == 403
    resp = client.post(
        "/api/documents/upload",
        files=[("files", ("a.txt", b"x", "text/plain"))],
        headers=headers,
    )
    assert resp.status_code == 403


def test_upload_and_process_success(client, admin_headers, fake_ingestion):
    result = _upload_txt(client, admin_headers)
    assert result["status"] == "pending"  # 上传立即返回，后台处理

    doc = _wait_status(client, admin_headers, result["document_id"])
    assert doc["status"] == "success"
    assert doc["chunk_count"] >= 1

    # 列表可见
    page = client.get("/api/documents", headers=admin_headers).json()
    assert page["total"] == 1
    assert page["items"][0]["filename"] == "退货政策.txt"

    # 分块预览
    chunks = client.get(
        f"/api/documents/{result['document_id']}/chunks", headers=admin_headers
    ).json()
    assert chunks["total"] == doc["chunk_count"]
    assert "退货" in chunks["items"][0]["content"]


def test_upload_invalid_type_rejected(client, admin_headers):
    resp = client.post(
        "/api/documents/upload",
        files=[("files", ("evil.exe", b"xx", "application/octet-stream"))],
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert "error" in resp.json()[0]
    assert client.get("/api/documents", headers=admin_headers).json()["total"] == 0


def test_delete_removes_everything(client, admin_headers, fake_ingestion):
    doc_id = _upload_txt(client, admin_headers)["document_id"]
    _wait_status(client, admin_headers, doc_id)

    assert client.delete(f"/api/documents/{doc_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/api/documents/{doc_id}", headers=admin_headers).status_code == 404
    assert client.get("/api/documents", headers=admin_headers).json()["total"] == 0


def test_reprocess_is_idempotent(client, admin_headers, fake_ingestion):
    doc_id = _upload_txt(client, admin_headers)["document_id"]
    first = _wait_status(client, admin_headers, doc_id)
    assert first["status"] == "success"

    resp = client.post(f"/api/documents/{doc_id}/reprocess", headers=admin_headers)
    assert resp.status_code == 204

    second = _wait_status(client, admin_headers, doc_id)
    assert second["status"] == "success"
    assert second["chunk_count"] == first["chunk_count"]  # 幂等：旧数据已清，块数不变


def test_missing_document_404(client, admin_headers):
    assert client.get("/api/documents/99999", headers=admin_headers).status_code == 404
    assert client.delete("/api/documents/99999", headers=admin_headers).status_code == 404
