import { fallbackHealthStatus, getHealthStatus } from "../lib/health";

const labels: Record<string, string> = {
  database: "PostgreSQL / pgvector",
  redis: "Redis",
  object_storage: "MinIO Object Storage",
};

export default async function Home() {
  let hasApiError = false;
  const health = await getHealthStatus().catch(() => {
    hasApiError = true;
    return fallbackHealthStatus();
  });
  const downServices = Object.values(health.services).filter((state) => state === "down").length;
  const statusLabel = hasApiError
    ? "API 응답을 가져오지 못했습니다."
    : downServices === 0
      ? "모든 기반 서비스가 정상입니다."
      : downServices === Object.keys(health.services).length
        ? "모든 기반 서비스가 응답하지 않습니다."
        : "일부 기반 서비스에 문제가 있습니다.";

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div className="rounded-2xl bg-slate-950 p-8 text-white shadow-lg">
        <p className="text-sm text-slate-300">SecureDocs AI Hub</p>
        <h1 className="mt-2 text-3xl font-bold">문서 관리 및 RAG 기반 AI 허브</h1>
        <p className="mt-3 max-w-3xl text-slate-300">
          중앙화된 문서 관리, 접근제어, 감사 로그, AI 추천과 권한 필터가 적용된 RAG 채팅을 위한 기반 환경입니다.
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">상태 요약</p>
        <p className="mt-2 text-lg font-semibold text-slate-900">{statusLabel}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {Object.entries(health.services).map(([name, state]) => (
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" key={name}>
            <p className="text-sm text-slate-500">{labels[name] ?? name}</p>
            <p className={`mt-3 text-2xl font-bold ${state === "up" ? "text-emerald-600" : "text-rose-600"}`}>{state}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">Backend API</p>
        <p className="mt-2 text-lg font-semibold">/api/v1/health 상태: {health.status}</p>
      </div>
    </section>
  );
}
