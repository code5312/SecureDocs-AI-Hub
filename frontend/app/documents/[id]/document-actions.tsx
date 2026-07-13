"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiClientError } from "../../../lib/api-shared";
import { deleteDocument, downloadDocument, downloadDocumentVersion, grantDocumentAcl, listDocumentAcl, retryDocumentVersionExtraction, revokeDocumentAcl, searchDocumentAclPrincipals, uploadDocumentVersion } from "../../../lib/documents-api";
import { documentPermissionLabels, extractionStatusLabels, formatFileSize, shortChecksum, type DocumentAclEntry, type DocumentAclPrincipalSearch, type DocumentPermission, type DocumentRecord, type DocumentVersion } from "../../../lib/documents";

const permissionOptions: DocumentPermission[] = ["VIEW_METADATA", "READ_CONTENT", "UPLOAD_VERSION", "DELETE", "MANAGE_ACL"];

function messageFrom(caught: unknown): string {
  return caught instanceof ApiClientError ? caught.message : "요청 처리 중 오류가 발생했습니다.";
}

function hasPermission(document: DocumentRecord, permission: DocumentPermission): boolean {
  return document.effective_permissions.includes(permission);
}

export function DocumentActions({ document, versions, onChanged }: { document: DocumentRecord; versions: DocumentVersion[]; onChanged: () => Promise<void> }) {
  const [isDownloading, setDownloading] = useState<string | null>(null);
  const [isUploadingVersion, setUploadingVersion] = useState(false);
  const [isDeleting, setDeleting] = useState(false);
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [retryingVersionId, setRetryingVersionId] = useState<string | null>(null);

  const canRead = hasPermission(document, "READ_CONTENT");
  const canUploadVersion = hasPermission(document, "UPLOAD_VERSION");
  const canDelete = hasPermission(document, "DELETE");
  const canManageAcl = hasPermission(document, "MANAGE_ACL");

  async function handleDownload(version?: DocumentVersion) {
    const key = version?.id ?? "current";
    if (isDownloading || !canRead) {
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
    if (!versionFile || isUploadingVersion || !canUploadVersion) {
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


  async function handleRetryExtraction(version: DocumentVersion) {
    if (!canUploadVersion || retryingVersionId) {
      return;
    }
    setRetryingVersionId(version.id);
    setMessage(null);
    try {
      await retryDocumentVersionExtraction(document.id, version.id);
      setMessage("문서 추출을 다시 요청했습니다.");
      await onChanged();
    } catch (caught) {
      setMessage(messageFrom(caught));
    } finally {
      setRetryingVersionId(null);
    }
  }

  async function handleDelete() {
    if (isDeleting || !canDelete || !confirm("문서를 논리 삭제하시겠습니까?")) {
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
        {canRead ? <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={Boolean(isDownloading)} onClick={() => void handleDownload()} type="button">{isDownloading === "current" ? "다운로드 중..." : "현재 버전 다운로드"}</button> : null}
        {canDelete ? <button className="rounded border border-rose-300 px-4 py-2 text-rose-700 disabled:opacity-60" disabled={isDeleting} onClick={handleDelete} type="button">{isDeleting ? "삭제 중..." : "논리 삭제"}</button> : null}
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

      <VersionHistory versions={versions} canRead={canRead} canRetry={canUploadVersion} isDownloading={isDownloading} retryingVersionId={retryingVersionId} onDownload={handleDownload} onRetry={handleRetryExtraction} />
      {canManageAcl ? <AclManager documentId={document.id} /> : null}
      {message ? <p className="text-sm text-slate-600">{message}</p> : null}
    </div>
  );
}

function VersionHistory({ versions, canRead, canRetry, isDownloading, retryingVersionId, onDownload, onRetry }: { versions: DocumentVersion[]; canRead: boolean; canRetry: boolean; isDownloading: string | null; retryingVersionId: string | null; onDownload: (version: DocumentVersion) => Promise<void>; onRetry: (version: DocumentVersion) => Promise<void> }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <h2 className="font-semibold">버전 이력</h2>
      {versions.length === 0 ? <p className="mt-2 text-sm text-slate-500">버전 이력이 없습니다.</p> : null}
      {versions.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b"><th className="py-2">버전</th><th>파일명</th><th>크기</th><th>MIME</th><th>추출 상태</th><th>청크</th><th>추출 완료</th><th>업로드 사용자</th><th>SHA-256</th><th>작업</th></tr></thead>
            <tbody>
              {versions.map((version) => (
                <tr className="border-b last:border-0" key={version.id}>
                  <td className="py-2">v{version.version_number} {version.is_current ? <span className="rounded bg-emerald-100 px-2 py-1 text-xs text-emerald-700">현재</span> : null}</td>
                  <td>{version.normalized_filename}</td>
                  <td>{formatFileSize(version.file_size)}</td>
                  <td>{version.mime_type}</td>
                  <td>{extractionStatusLabels[version.extraction_status]}{version.extraction_status === "FAILED" && version.extraction_error_message ? <p className="text-xs text-rose-600">{version.extraction_error_message}</p> : null}</td>
                  <td>{version.chunk_count}</td>
                  <td>{version.extracted_at ? new Date(version.extracted_at).toLocaleString() : "-"}</td>
                  <td>{version.uploaded_by}</td>
                  <td title={version.checksum_sha256}>{shortChecksum(version.checksum_sha256)}</td>
                  <td><div className="flex gap-2">{canRead ? <button className="rounded border px-3 py-1 disabled:opacity-60" disabled={Boolean(isDownloading)} onClick={() => void onDownload(version)} type="button">{isDownloading === version.id ? "다운로드 중..." : "다운로드"}</button> : <span className="text-slate-400">권한 없음</span>}{canRetry && version.extraction_status === "FAILED" ? <button className="rounded border px-3 py-1 text-amber-700 disabled:opacity-60" disabled={Boolean(retryingVersionId)} onClick={() => void onRetry(version)} type="button">{retryingVersionId === version.id ? "재시도 중..." : "추출 재시도"}</button> : null}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function AclManager({ documentId }: { documentId: string }) {
  const [entries, setEntries] = useState<DocumentAclEntry[]>([]);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<DocumentAclPrincipalSearch>({ users: [], departments: [] });
  const [selected, setSelected] = useState<{ type: "USER" | "DEPARTMENT"; id: string; label: string } | null>(null);
  const [permissions, setPermissions] = useState<DocumentPermission[]>(["VIEW_METADATA"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const principalOptions = useMemo(() => [
    ...results.users.map((user) => ({ type: "USER" as const, id: user.id, label: `${user.name} <${user.email}>` })),
    ...results.departments.map((department) => ({ type: "DEPARTMENT" as const, id: department.id, label: `부서: ${department.name}` })),
  ], [results]);

  const refreshAcl = useCallback(async () => {
    setError(null);
    try {
      setEntries(await listDocumentAcl(documentId));
    } catch (caught) {
      setError(messageFrom(caught));
    }
  }, [documentId]);

  useEffect(() => {
    void refreshAcl();
  }, [refreshAcl]);

  async function handleSearch() {
    if (search.trim().length < 2) {
      setError("검색어는 최소 2자 이상 입력하세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResults(await searchDocumentAclPrincipals(documentId, search));
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  async function handleGrant() {
    if (!selected || permissions.length === 0 || busy) {
      setError("대상과 권한을 선택하세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setEntries(await grantDocumentAcl({ documentId, principalType: selected.type, principalId: selected.id, permissions }));
      setSelected(null);
      setSearch("");
      setResults({ users: [], departments: [] });
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(entryId: string) {
    if (busy || !confirm("이 권한을 삭제하시겠습니까?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await revokeDocumentAcl(documentId, entryId);
      await refreshAcl();
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  function togglePermission(permission: DocumentPermission) {
    setPermissions((current) => current.includes(permission) ? current.filter((item) => item !== permission) : [...current, permission]);
  }

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <h2 className="font-semibold">공유 및 권한</h2>
      <p className="mt-1 text-sm text-slate-500">owner와 SYSTEM_ADMIN은 ACL row 없이도 전체 권한을 유지합니다. 이 UI는 편의용이며 backend 권한 검사가 최종 보안 경계입니다.</p>
      <div className="mt-4 grid gap-3 rounded bg-slate-50 p-3">
        <div className="flex gap-2">
          <input className="flex-1 rounded border p-2" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="사용자 이름·이메일 또는 부서명 검색" />
          <button className="rounded border px-3 py-2 disabled:opacity-60" disabled={busy} onClick={() => void handleSearch()} type="button">검색</button>
        </div>
        {principalOptions.length > 0 ? <select className="rounded border p-2" value={selected ? `${selected.type}:${selected.id}` : ""} onChange={(event) => setSelected(principalOptions.find((item) => `${item.type}:${item.id}` === event.target.value) ?? null)}><option value="">권한 대상 선택</option>{principalOptions.map((option) => <option key={`${option.type}:${option.id}`} value={`${option.type}:${option.id}`}>{option.label}</option>)}</select> : null}
        <div className="grid gap-2 md:grid-cols-2">
          {permissionOptions.map((permission) => <label className="flex items-center gap-2 text-sm" key={permission}><input checked={permissions.includes(permission)} onChange={() => togglePermission(permission)} type="checkbox" />{documentPermissionLabels[permission]}</label>)}
        </div>
        <button className="w-fit rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={busy} onClick={() => void handleGrant()} type="button">권한 추가</button>
      </div>
      {entries.length === 0 ? <p className="mt-3 text-sm text-slate-500">명시적으로 부여된 ACL entry가 없습니다.</p> : null}
      {entries.length > 0 ? <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="py-2">대상</th><th>권한</th><th>부여자</th><th>작업</th></tr></thead><tbody>{entries.map((entry) => <tr className="border-b last:border-0" key={entry.id}><td className="py-2">{entry.user ? `${entry.user.name} <${entry.user.email}>` : `부서: ${entry.department?.name ?? "알 수 없음"}`}</td><td>{documentPermissionLabels[entry.permission]}</td><td>{entry.granted_by ?? "-"}</td><td><button className="rounded border px-3 py-1 text-rose-700 disabled:opacity-60" disabled={busy} onClick={() => void handleRevoke(entry.id)} type="button">삭제</button></td></tr>)}</tbody></table></div> : null}
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}
