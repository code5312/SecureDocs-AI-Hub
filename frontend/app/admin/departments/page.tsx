import { ProtectedRoute } from "../../../components/protected-route";

export default function AdminDepartmentsPage() {
  return (
    <ProtectedRoute allowedRoles={["SYSTEM_ADMIN"]}>
      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between"><h1 className="text-2xl font-bold">부서 관리</h1><button className="rounded bg-slate-950 px-4 py-2 text-white">부서 생성</button></div>
        <p className="rounded bg-slate-50 p-4 text-slate-600">부서 계층, 활성 상태, 생성/수정 기능을 연결할 관리자 화면입니다. 실제 권한 검사는 백엔드 SYSTEM_ADMIN 정책이 담당합니다.</p>
      </section>
    </ProtectedRoute>
  );
}
