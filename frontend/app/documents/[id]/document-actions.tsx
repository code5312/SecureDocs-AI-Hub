"use client";

import { useState } from "react";

import { ApiClientError } from "../../../lib/api-shared";
import { downloadDocument } from "../../../lib/documents-api";

export function DocumentActions({ documentId, fallbackFilename }: { documentId: string; fallbackFilename?: string }) {
  const [isDownloading, setDownloading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleDownload() {
    if (isDownloading) {
      return;
    }
    setDownloading(true);
    setMessage(null);
    try {
      await downloadDocument(documentId, fallbackFilename);
      setMessage("다운로드를 시작했습니다.");
    } catch (caught) {
      setMessage(caught instanceof ApiClientError ? caught.message : "다운로드 중 오류가 발생했습니다.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <button className="rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isDownloading} onClick={handleDownload} type="button">
          {isDownloading ? "다운로드 중..." : "다운로드"}
        </button>
        <button className="rounded border border-rose-300 px-4 py-2 text-rose-700" type="button">삭제</button>
      </div>
      {message ? <p className="text-sm text-slate-600">{message}</p> : null}
    </div>
  );
}
