"use client";

import { useState } from "react";

import { ApiClientError } from "../../../lib/api-shared";
import { deleteDocument, downloadDocument, downloadDocumentVersion, uploadDocumentVersion } from "../../../lib/documents-api";
import { formatFileSize, shortChecksum, type DocumentRecord, type DocumentVersion } from "../../../lib/documents";
import { useAuthStore } from "../../../lib/auth-store";

function messageFrom(caught: unknown): string {
  return caught instanceof ApiClientError ? caught.message : "요청 처리 중 오류가 발생했습니다.";
}

export function DocumentActions({ document, versions, onChanged }: { document: DocumentRecord; versions: DocumentVersion[]; onChanged: () => Promise<void> }) {
  const user = useAuthStore((state) => state.user);
  const [isDownloading, setDownloading] = useState<string | null>(null);
  const [isUploadingVersion, setUploadingVersion] = useState(false);
  const [isDeleting, setDeleting] = useState(false);
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canUploadVersion = Boolean(user && (user.role === "SYSTEM_ADMIN" || user.id === document.owner_id));

  async function handleDownload(version?: DocumentVersion) {
    const key = version?.id ?? "current";
    if (isDownloading) {
      return;
    }
    setDownloading(key);
    setMessage(null);
    try {
      if (version) {
        await downloadDocumentVersion(document.id, version.id, version.normalized_filename);
      } else {
        await downloadDocument(document.id, document.current_version?.normalized_filename);
      }
      setMessage("다운로드를 시작했습니다.");
    } catch (caught) {
      setMessage(messageFrom(caught));
    } finally {
      setDownloading(null);
    }
  }

  async function handleUploadVersion() {
    if (!versionFile || isUploadingVersion) {
      setMessage("새 버전 파일을 선택하세요.");
      return;
    }
    setUploadingVersion(true);
    setMessage(null);
    try {
      await uploadDocumentVersion(document.id, versionFile);
      setVersionFile(null);
      setMessage("새 버전을 업로드했습니다.");
      await onChanged();
    } catch (caught) {
      setMessage(messageFrom(caught));
    } finally {
      setUploadingVersion(false);
    }
  }

  async function handleDelete() {
    if (isDeleting || !confirm("문서를 논리 삭제하시겠습니까?")) {
      return;
    }
    setDeleting(true);
    setMessage(null);
    try {
      await deleteDocument(document.id);
      setMessage("문서를 삭제했습니다.");
      await onChanged();
    } catch (caught) {
      setMessage(messageFrom(caught));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={Boolean(isDownloading)} onClick={() => void handleDownload()} type="button">
          {isDownloading === "current" ? "다운로드 중..." : "현재 버전 다운로드"}
        </button>
        <button className="rounded border border-rose-300 px-4 py-2 text-rose-700 disabled:opacity-60" disabled={isDeleting} onClick={handleDelete} type="button">{isDeleting ? "삭제 중..." : "논리 삭제"}</button>
      </div>

      {canUploadVersion ? (
        <div className="rounded-lg border border-slate-200 p-4">
          <h2 className="font-semibold">새 버전 업로드</h2>
          <p className="mt-1 text-sm text-slate-500">문서 제목과 설명은 변경하지 않고 파일만 새 버전으로 추가합니다. 현재 버전과 동일한 SHA-256 파일은 거부됩니다.</p>
          <div className="mt-3 flex flex-col gap-3 md:flex-row">
            <input className="rounded border p-2" onChange={(event) => setVersionFile(event.target.files?.[0] ?? null)} type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md" />
            <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isUploadingVersion} onClick={() => void handleUploadVersion()} type="button">{isUploadingVersion ? "업로드 중..." : "새 버전 업로드"}</button>
          </div>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 p-4">
        <h2 className="font-semibold">버전 이력</h2>
        {versions.length === 0 ? <p className="mt-2 text-sm text-slate-500">버전 이력이 없습니다.</p> : null}
        {versions.length > 0 ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b"><th className="py-2">버전</th><th>파일명</th><th>크기</th><th>MIME</th><th>업로드 사용자</th><th>SHA-256</th><th>작업</th></tr></thead>
              <tbody>
                {versions.map((version) => (
                  <tr className="border-b last:border-0" key={version.id}>
                    <td className="py-2">v{version.version_number} {version.is_current ? <span className="rounded bg-emerald-100 px-2 py-1 text-xs text-emerald-700">현재</span> : null}</td>
                    <td>{version.normalized_filename}</td>
                    <td>{formatFileSize(version.file_size)}</td>
                    <td>{version.mime_type}</td>
                    <td>{version.uploaded_by}</td>
                    <td title={version.checksum_sha256}>{shortChecksum(version.checksum_sha256)}</td>
                    <td><button className="rounded border px-3 py-1 disabled:opacity-60" disabled={Boolean(isDownloading)} onClick={() => void handleDownload(version)} type="button">{isDownloading === version.id ? "다운로드 중..." : "다운로드"}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
      {message ? <p className="text-sm text-slate-600">{message}</p> : null}
    </div>
  );
}
