import { ProtectedRoute } from "../../components/protected-route";
import { allowedDocumentExtensions, type DocumentListItem } from "../../lib/documents";

const documents: DocumentListItem[] = [];

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <section className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div><h1 className="text-2xl font-bold">문서 목록</h1><p className="text-sm text-slate-500">임시 역할 정책에 따라 백엔드가 목록/다운로드 권한을 다시 검증합니다.</p></div>
            <button className="rounded bg-slate-950 px-4 py-2 text-white">업로드</button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3"><input className="rounded border p-2" placeholder="제목 검색" /><select className="rounded border p-2"><option>전체 상태</option><option>ACTIVE</option><option>PROCESSING</option><option>FAILED</option></select><button className="rounded border p-2">검색</button></div>
        </div>
        <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">문서 업로드</h2>
          <input className="w-full rounded border p-2" placeholder="제목" />
          <textarea className="w-full rounded border p-2" placeholder="설명" />
          <input className="w-full rounded border p-2" type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md" />
          <p className="text-sm text-slate-500">허용 형식: {allowedDocumentExtensions.join(", ")} · 최대 50MB. 브라우저 검증은 편의용이며 백엔드 검증이 최종 기준입니다.</p>
          <button className="rounded bg-slate-950 px-4 py-2 text-white" type="button">업로드 시작</button>
        </form>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          {documents.length === 0 ? <p className="text-slate-500">표시할 문서가 없습니다.</p> : null}
        </div>
      </section>
    </ProtectedRoute>
  );
}
