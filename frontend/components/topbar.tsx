"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { roleLabels } from "../lib/auth";
import { useAuthStore } from "../lib/auth-store";

export function Topbar() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const status = useAuthStore((state) => state.status);
  const logout = useAuthStore((state) => state.logout);
  const [isLoggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    await logout();
    router.replace("/login");
    setLoggingOut(false);
  }

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">관리자 콘솔</p>
        <h2 className="text-xl font-semibold text-slate-950">SecureDocs AI Hub</h2>
      </div>
      <div className="flex items-center gap-4">
        <div className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700">알림 0건</div>
        {status === "authenticated" && user ? (
          <div className="text-right text-sm">
            <p className="font-medium text-slate-900">{user.name}</p>
            <p className="text-slate-500">{user.email}</p>
            <p className="text-xs text-slate-500">{roleLabels[user.role]} · 부서 {user.department_id ?? "미지정"}</p>
          </div>
        ) : (
          <div className="text-right text-sm"><p className="font-medium text-slate-900">로그인 필요</p><p className="text-slate-500">인증 후 사용자 정보 표시</p></div>
        )}
        <button className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-60" disabled={status !== "authenticated" || isLoggingOut} onClick={handleLogout} type="button">
          {isLoggingOut ? "로그아웃 중..." : "로그아웃"}
        </button>
      </div>
    </header>
  );
}
