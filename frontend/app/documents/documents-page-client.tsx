"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ProtectedRoute } from "../../components/protected-route";
import { ApiClientError } from "../../lib/api-shared";
import { listDocuments, uploadDocument } from "../../lib/documents-api";
import { allowedDocumentExtensions, formatFileSize, type DocumentRecord, type DocumentStatus } from "../../lib/documents";

const PAGE_SIZE = 20;

function errorMessage(caught: unknown): string {
  return caught instanceof ApiClientError ? caught.message : "문서 요청 중 오류가 발생했습니다.";
}

export function DocumentsPageClient() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<DocumentStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [isLoading, setLoading] = useState(true);
  const [isUploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  async function loadDocuments(nextOffset = offset) {
    setLoading(true);
    setError(null);
    try {
      const result = await listDocuments({ title, status, offset: nextOffset, limit: PAGE_SIZE });
      setDocuments(result);
      setOffset(nextOffset);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadDocuments(0);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFile || !uploadTitle.trim() || isUploading) {
      setMessage("제목과 파일을 선택하세요.");
      return;
    }
    setUploading(true);
    setMessage(null);
    setError(null);
    try {
      await uploadDocument({ title: uploadTitle.trim(), description: uploadDescription.trim() || undefined, file: uploadFile });
      setUploadTitle("");
      setUploadDescription("");
      setUploadFile(null);
      setMessage("문서를 업로드했습니다.");
      await loadDocuments(0);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setUploading(false);
    }
  }

  return (
    <ProtectedRoute>
      <section className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl font-bold">문서 목록</h1>
              <p className="text-sm text-slate-500">임시 역할 정책에 따라 백엔드가 목록/다운로드 권한을 다시 검증합니다.</p>
            </div>
          </div>
          <form className="mt-4 grid gap-3 md:grid-cols-4" onSubmit={handleSearch}>
            <input className="rounded border p-2" onChange={(event) => setTitle(event.target.value)} placeholder="제목 검색" value={title} />
            <select className="rounded border p-2" onChange={(event) => setStatus(event.target.value as DocumentStatus | "")} value={status}>
              <option value="">전체 상태</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="PROCESSING">PROCESSING</option>
              <option value="FAILED">FAILED</option>
            </select>
            <button className="rounded border p-2" disabled={isLoading} type="submit">검색</button>
            <button className="rounded border p-2" disabled={offset === 0 || isLoading} onClick={() => void loadDocuments(Math.max(0, offset - PAGE_SIZE))} type="button">이전</button>
          </form>
        </div>

        <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={handleUpload}>
          <h2 className="text-xl font-semibold">문서 업로드</h2>
          <input className="w-full rounded border p-2" onChange={(event) => setUploadTitle(event.target.value)} placeholder="제목" value={uploadTitle} />
          <textarea className="w-full rounded border p-2" onChange={(event) => setUploadDescription(event.target.value)} placeholder="설명" value={uploadDescription} />
          <input className="w-full rounded border p-2" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md" />
          <p className="text-sm text-slate-500">허용 형식: {allowedDocumentExtensions.join(", ")} · 최대 50MB. 브라우저 검증은 편의용이며 백엔드 검증이 최종 기준입니다.</p>
          <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isUploading} type="submit">{isUploading ? "업로드 중..." : "업로드 시작"}</button>
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
        </form>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
          {isLoading ? <p className="text-slate-500">문서 목록을 불러오는 중입니다...</p> : null}
          {!isLoading && documents.length === 0 ? <p className="text-slate-500">표시할 문서가 없습니다.</p> : null}
          {documents.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead><tr className="border-b"><th className="py-2">제목</th><th>현재 파일</th><th>크기</th><th>상태</th><th>생성일</th></tr></thead>
                <tbody>
                  {documents.map((document) => (
                    <tr className="border-b last:border-0" key={document.id}>
                      <td className="py-2"><Link className="font-medium text-slate-950 underline" href={`/documents/${document.id}`}>{document.title}</Link></td>
                      <td>{document.current_version?.normalized_filename ?? "-"}</td>
                      <td>{document.current_version ? formatFileSize(document.current_version.file_size) : "-"}</td>
                      <td>{document.status}</td>
                      <td>{new Date(document.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 flex justify-end gap-2">
                <button className="rounded border px-3 py-2 disabled:opacity-50" disabled={offset === 0 || isLoading} onClick={() => void loadDocuments(Math.max(0, offset - PAGE_SIZE))} type="button">이전</button>
                <button className="rounded border px-3 py-2 disabled:opacity-50" disabled={documents.length < PAGE_SIZE || isLoading} onClick={() => void loadDocuments(offset + PAGE_SIZE)} type="button">다음</button>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </ProtectedRoute>
  );
}
