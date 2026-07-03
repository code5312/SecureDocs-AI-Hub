export function Topbar() {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">관리자 콘솔</p>
        <h2 className="text-xl font-semibold text-slate-950">시스템 상태</h2>
      </div>
      <div className="flex items-center gap-4">
        <div className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700">알림 0건</div>
        <button className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">Admin</button>
      </div>
    </header>
  );
}
