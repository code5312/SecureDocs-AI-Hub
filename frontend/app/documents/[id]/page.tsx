"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ProtectedRoute } from "../../../components/protected-route";
import { ApiClientError } from "../../../lib/api-shared";
import { deleteDocument, getDocument, getDocumentDownloadUrl } from "../../../lib/documents-api";
import { documentStatusLabels, formatDocumentDate, formatFileSize, type DocumentRecord } from "../../../lib/documents";

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message;
  return "문서 요청 중 네트워크 오류가 발생했습니다.";
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const documentId = params.id;
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setDownloading] = useState(false);
  const [isDeleting, setDeleting] = useState(false);

  const loadDocument = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocument(await getDocument(documentId));
    } catch (caught) {
      setDocument(null);
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void loadDocument();
  }, [loadDocument]);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      const result = await getDocumentDownloadUrl(documentId);
      window.location.assign(result.url);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setDownloading(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("문서를 삭제 처리하시겠습니까? 원본 파일은 보존 정책에 따라 유지됩니다.")) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteDocument(documentId);
      router.replace("/documents");
    } catch (caught) {
      setError(errorMessage(caught));
      setDeleting(false);
    }
  }

  return (
    <ProtectedRoute>
      <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link className="text-sm text-slate-500 hover:underline" href="/documents">← 문서 목록</Link>
            <h1 className="mt-2 text-2xl font-bold">{document?.title ?? "문서 상세"}</h1>
            <p className="mt-1 break-all text-xs text-slate-500">문서 ID: {documentId}</p>
          </div>
          {document ? <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">{documentStatusLabels[document.status]}</span> : null}
        </div>

        {isLoading ? <p className="rounded bg-slate-50 p-4 text-slate-600">문서 정보를 불러오는 중입니다...</p> : null}
        {error ? <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}<button className="ml-3 underline" onClick={() => void loadDocument()} type="button">다시 시도</button></div> : null}

        {!isLoading && document ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-4"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">설명</p><p className="mt-2 whitespace-pre-wrap text-slate-800">{document.description || "등록된 설명이 없습니다."}</p></div>
              <div className="rounded-lg border border-slate-200 p-4"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">소유 정보</p><dl className="mt-2 space-y-2 text-sm"><div><dt className="text-slate-500">소유자 ID</dt><dd className="break-all font-mono">{document.owner_id}</dd></div><div><dt className="text-slate-500">부서 ID</dt><dd className="break-all font-mono">{document.department_id ?? "미지정"}</dd></div></dl></div>
            </div>

            <div className="rounded-lg border border-slate-200 p-4">
              <h2 className="font-semibold">현재 버전</h2>
              {document.current_version ? (
                <dl className="mt-3 grid gap-4 text-sm md:grid-cols-2 lg:grid-cols-3">
                  <div><dt className="text-slate-500">파일명</dt><dd className="break-all">{document.current_version.normalized_filename}</dd></div>
                  <div><dt className="text-slate-500">버전</dt><dd>v{document.current_version.version_number}</dd></div>
                  <div><dt className="text-slate-500">파일 크기</dt><dd>{formatFileSize(document.current_version.file_size)}</dd></div>
                  <div><dt className="text-slate-500">MIME 타입</dt><dd className="break-all">{document.current_version.mime_type}</dd></div>
                  <div><dt className="text-slate-500">등록 시각</dt><dd>{formatDocumentDate(document.current_version.created_at)}</dd></div>
                  <div><dt className="text-slate-500">SHA-256</dt><dd className="break-all font-mono text-xs">{document.current_version.checksum_sha256}</dd></div>
                </dl>
              ) : <p className="mt-2 text-slate-500">연결된 파일 버전이 없습니다.</p>}
            </div>

            <div className="rounded-lg border border-slate-200 p-4 text-sm"><p>생성: {formatDocumentDate(document.created_at)}</p><p className="mt-1">최종 수정: {formatDocumentDate(document.updated_at)}</p></div>

            <div className="flex flex-wrap gap-2">
              <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={!document.current_version || isDownloading || isDeleting} onClick={() => void handleDownload()} type="button">{isDownloading ? "다운로드 준비 중..." : "다운로드"}</button>
              <button className="rounded border border-rose-300 px-4 py-2 text-rose-700 disabled:opacity-60" disabled={isDeleting || isDownloading} onClick={() => void handleDelete()} type="button">{isDeleting ? "삭제 처리 중..." : "문서 삭제"}</button>
            </div>
          </>
        ) : null}
      </section>
    </ProtectedRoute>
  );
}
