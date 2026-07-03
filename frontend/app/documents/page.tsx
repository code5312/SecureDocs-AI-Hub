"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ProtectedRoute } from "../../components/protected-route";
import { ApiClientError } from "../../lib/api-shared";
import { listDocuments, uploadDocument } from "../../lib/documents-api";
import {
  allowedDocumentExtensions,
  documentStatusLabels,
  formatDocumentDate,
  formatFileSize,
  type DocumentRecord,
  type DocumentStatus,
} from "../../lib/documents";

const PAGE_SIZE = 20;

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message;
  return "문서 요청 중 네트워크 오류가 발생했습니다.";
}

export default function DocumentsPage() {
  const uploadSectionRef = useRef<HTMLFormElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [titleFilter, setTitleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | "">("");
  const [appliedTitle, setAppliedTitle] = useState("");
  const [appliedStatus, setAppliedStatus] = useState<DocumentStatus | "">("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listDocuments({
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        title: appliedTitle,
        status: appliedStatus,
      });
      setDocuments(result);
    } catch (caught) {
      setDocuments([]);
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [appliedStatus, appliedTitle, page]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(0);
    setAppliedTitle(titleFilter.trim());
    setAppliedStatus(statusFilter);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadMessage(null);
    if (!uploadTitle.trim()) {
      setUploadMessage("문서 제목을 입력해 주세요.");
      return;
    }
    if (!uploadFile) {
      setUploadMessage("업로드할 파일을 선택해 주세요.");
      return;
    }

    setUploading(true);
    try {
      await uploadDocument({ title: uploadTitle, description: uploadDescription, file: uploadFile });
      setUploadMessage("문서가 안전하게 업로드되었습니다.");
      setUploadTitle("");
      setUploadDescription("");
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (page === 0) await loadDocuments();
      else setPage(0);
    } catch (caught) {
      setUploadMessage(errorMessage(caught));
    } finally {
      setUploading(false);
    }
  }

  return (
    <ProtectedRoute>
      <section className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">문서 목록</h1>
              <p className="text-sm text-slate-500">조회·다운로드 권한은 모든 요청에서 백엔드가 다시 검증합니다.</p>
            </div>
            <button className="rounded bg-slate-950 px-4 py-2 text-white" onClick={() => uploadSectionRef.current?.scrollIntoView({ behavior: "smooth" })} type="button">
              문서 업로드
            </button>
          </div>
          <form className="mt-4 grid gap-3 md:grid-cols-[1fr_220px_auto]" onSubmit={applyFilters}>
            <input className="rounded border p-2" placeholder="제목 검색" value={titleFilter} onChange={(event) => setTitleFilter(event.target.value)} />
            <select className="rounded border p-2" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as DocumentStatus | "")}>
              <option value="">전체 상태</option>
              {Object.entries(documentStatusLabels).map(([status, label]) => <option key={status} value={status}>{label}</option>)}
            </select>
            <button className="rounded border px-4 py-2" type="submit">검색</button>
          </form>
        </div>

        <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" id="document-upload" onSubmit={submitUpload} ref={uploadSectionRef}>
          <h2 className="text-xl font-semibold">문서 업로드</h2>
          <label className="block text-sm font-medium">제목<input className="mt-1 w-full rounded border p-2" maxLength={255} required value={uploadTitle} onChange={(event) => setUploadTitle(event.target.value)} /></label>
          <label className="block text-sm font-medium">설명<textarea className="mt-1 min-h-24 w-full rounded border p-2" value={uploadDescription} onChange={(event) => setUploadDescription(event.target.value)} /></label>
          <label className="block text-sm font-medium">파일<input className="mt-1 w-full rounded border p-2" ref={fileInputRef} type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md" required onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} /></label>
          <p className="text-sm text-slate-500">허용 형식: {allowedDocumentExtensions.join(", ")} · 최대 50MB. 브라우저 검증은 편의용이며 백엔드 검증이 최종 기준입니다.</p>
          {uploadMessage ? <p className="rounded bg-slate-50 p-3 text-sm text-slate-700">{uploadMessage}</p> : null}
          <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isUploading} type="submit">{isUploading ? "업로드 중..." : "업로드 시작"}</button>
        </form>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {error ? <div className="border-b border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}<button className="ml-3 underline" onClick={() => void loadDocuments()} type="button">다시 시도</button></div> : null}
          {isLoading ? <p className="p-6 text-slate-500">문서 목록을 불러오는 중입니다...</p> : null}
          {!isLoading && !error && documents.length === 0 ? <p className="p-6 text-slate-500">조건에 맞는 문서가 없습니다.</p> : null}
          {!isLoading && documents.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-slate-600"><tr><th className="px-4 py-3">문서</th><th className="px-4 py-3">상태</th><th className="px-4 py-3">파일</th><th className="px-4 py-3">소유자</th><th className="px-4 py-3">등록일</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {documents.map((document) => (
                    <tr key={document.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3"><Link className="font-medium text-slate-950 hover:underline" href={`/documents/${document.id}`}>{document.title}</Link><p className="max-w-md truncate text-xs text-slate-500">{document.description || "설명 없음"}</p></td>
                      <td className="px-4 py-3"><span className="rounded-full bg-slate-100 px-2 py-1 text-xs">{documentStatusLabels[document.status]}</span></td>
                      <td className="px-4 py-3">{document.current_version ? <><p>{document.current_version.normalized_filename}</p><p className="text-xs text-slate-500">{formatFileSize(document.current_version.file_size)}</p></> : <span className="text-slate-400">버전 없음</span>}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{document.owner_id.slice(0, 8)}…</td>
                      <td className="px-4 py-3 text-slate-600">{formatDocumentDate(document.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
            <p className="text-sm text-slate-500">페이지 {page + 1}</p>
            <div className="flex gap-2"><button className="rounded border px-3 py-1.5 disabled:opacity-40" disabled={page === 0 || isLoading} onClick={() => setPage((value) => Math.max(0, value - 1))} type="button">이전</button><button className="rounded border px-3 py-1.5 disabled:opacity-40" disabled={documents.length < PAGE_SIZE || isLoading} onClick={() => setPage((value) => value + 1)} type="button">다음</button></div>
          </div>
        </div>
      </section>
    </ProtectedRoute>
  );
}
