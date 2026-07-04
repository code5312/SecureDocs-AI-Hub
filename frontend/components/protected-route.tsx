"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import type { Role } from "../lib/auth";
import { useAuthStore } from "../lib/auth-store";

export function ProtectedRoute({ children, allowedRoles }: { children: ReactNode; allowedRoles?: Role[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [pathname, router, status]);

  if (status === "loading") {
    return <div className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600 shadow-sm">인증 상태를 확인하는 중입니다...</div>;
  }

  if (status === "unauthenticated") {
    return <div className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600 shadow-sm">로그인 화면으로 이동하는 중입니다...</div>;
  }

  if (allowedRoles && (!user || !allowedRoles.includes(user.role))) {
    return <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-800 shadow-sm">이 페이지에 접근할 권한이 없습니다.</div>;
  }

  return children;
}
