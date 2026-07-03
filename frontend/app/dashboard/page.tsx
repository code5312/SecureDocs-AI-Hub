import { ProtectedRoute } from "../../components/protected-route";

export default function Page() {
  return (
    <ProtectedRoute>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">dashboard 화면은 향후 기능 구현 범위입니다.</div>
    </ProtectedRoute>
  );
}
