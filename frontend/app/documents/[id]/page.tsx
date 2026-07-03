import { ProtectedRoute } from "../../../components/protected-route";
import { DocumentActions } from "./document-actions";

export default async function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <ProtectedRoute>
      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">문서 상세</h1>
        <p className="text-sm text-slate-500">문서 ID: {id}</p>
        <div className="rounded bg-slate-50 p-4 text-slate-600">메타데이터, 현재 버전, 다운로드, 논리 삭제 UI가 API 연결 후 표시됩니다.</div>
        <DocumentActions documentId={id} />
      </section>
    </ProtectedRoute>
  );
}
