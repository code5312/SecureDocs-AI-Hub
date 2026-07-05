import { ProtectedRoute } from "../../../components/protected-route";
import { roleLabels, type UserSummary } from "../../../lib/auth";

const demoRows: UserSummary[] = [];

export default function AdminUsersPage() {
  return (
    <ProtectedRoute allowedRoles={["SYSTEM_ADMIN"]}>
      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between"><h1 className="text-2xl font-bold">사용자 관리</h1><button className="rounded bg-slate-950 px-4 py-2 text-white">사용자 생성</button></div>
        <div className="grid gap-3 md:grid-cols-4"><input className="rounded border p-2" placeholder="이메일 필터" /><input className="rounded border p-2" placeholder="이름 필터" /><select className="rounded border p-2"><option>전체 역할</option>{Object.entries(roleLabels).map(([role, label]) => <option key={role}>{label}</option>)}</select><select className="rounded border p-2"><option>전체 상태</option><option>활성</option><option>비활성</option></select></div>
        {demoRows.length === 0 ? <p className="rounded bg-slate-50 p-4 text-slate-600">API 연결 후 사용자 목록, 페이지네이션, 생성/수정 폼이 표시됩니다. 권한이 없으면 백엔드에서 차단됩니다.</p> : null}
      </section>
    </ProtectedRoute>
  );
}
