export default function DocumentDetailPage({ params }: { params: { id: string } }) {
  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold">문서 상세</h1>
      <p className="text-sm text-slate-500">문서 ID: {params.id}</p>
      <div className="rounded bg-slate-50 p-4 text-slate-600">메타데이터, 현재 버전, 다운로드, 논리 삭제 UI가 API 연결 후 표시됩니다.</div>
      <div className="flex gap-2"><button className="rounded bg-slate-950 px-4 py-2 text-white">다운로드</button><button className="rounded border border-rose-300 px-4 py-2 text-rose-700">삭제</button></div>
    </section>
  );
}
