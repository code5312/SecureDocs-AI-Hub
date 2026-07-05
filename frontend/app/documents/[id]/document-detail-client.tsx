"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "../../../components/protected-route";
import { ApiClientError } from "../../../lib/api-shared";
import { getDocument, listDocumentVersions } from "../../../lib/documents-api";
import { formatFileSize, type DocumentRecord, type DocumentVersion } from "../../../lib/documents";
import { DocumentActions } from "./document-actions";

function errorMessage(caught: unknown): string {
  return caught instanceof ApiClientError ? caught.message : "문서 상세를 불러오는 중 오류가 발생했습니다.";
}

export function DocumentDetailClient({ documentId }: { documentId: string }) {
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [nextDocument, nextVersions] = await Promise.all([getDocument(documentId), listDocumentVersions(documentId)]);
      setDocument(nextDocument);
      setVersions(nextVersions);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  return (
    <ProtectedRoute>
      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">문서 상세</h1>
        {isLoading ? <p className="text-slate-500">문서 정보를 불러오는 중입니다...</p> : null}
        {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        {document ? (
          <>
            <div className="grid gap-3 rounded bg-slate-50 p-4 text-sm text-slate-700 md:grid-cols-2">
              <p><span className="font-semibold">제목:</span> {document.title}</p>
              <p><span className="font-semibold">상태:</span> {document.status}</p>
              <p><span className="font-semibold">문서 ID:</span> {document.id}</p>
              <p><span className="font-semibold">소유자:</span> {document.owner_id}</p>
              <p><span className="font-semibold">부서:</span> {document.department_id ?? "-"}</p>
              <p><span className="font-semibold">현재 버전 ID:</span> {document.current_version_id ?? "-"}</p>
              <p><span className="font-semibold">생성:</span> {new Date(document.created_at).toLocaleString()}</p>
              <p><span className="font-semibold">수정:</span> {new Date(document.updated_at).toLocaleString()}</p>
              <p className="md:col-span-2"><span className="font-semibold">설명:</span> {document.description ?? "-"}</p>
            </div>
            <div className="rounded border border-slate-200 p-4 text-sm">
              <h2 className="font-semibold">현재 버전</h2>
              {document.current_version ? (
                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <p>v{document.current_version.version_number} · {document.current_version.normalized_filename}</p>
                  <p>{document.current_version.mime_type}</p>
                  <p>{formatFileSize(document.current_version.file_size)}</p>
                  <p className="break-all">SHA-256: {document.current_version.checksum_sha256}</p>
                </div>
              ) : <p className="mt-2 text-slate-500">현재 버전이 없습니다.</p>}
            </div>
            <DocumentActions document={document} versions={versions} onChanged={load} />
          </>
        ) : null}
      </section>
    </ProtectedRoute>
  );
}
