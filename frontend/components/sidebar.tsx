"use client";

import Link from "next/link";

import { isSystemAdmin } from "../lib/auth";
import { useAuthStore } from "../lib/auth-store";

type NavigationItem = {
  label: string;
  href: string;
  adminOnly?: boolean;
};

const navigationItems: NavigationItem[] = [
  { label: "대시보드", href: "/dashboard" },
  { label: "문서", href: "/documents" },
  { label: "사용자 관리", href: "/admin/users", adminOnly: true },
  { label: "부서 관리", href: "/admin/departments", adminOnly: true },
];

export function Sidebar() {
  const user = useAuthStore((state) => state.user);
  const visibleItems = navigationItems.filter((item) => !item.adminOnly || isSystemAdmin(user));

  return (
    <aside className="hidden min-h-screen w-64 border-r border-slate-200 bg-white p-6 lg:block">
      <h1 className="text-lg font-bold text-slate-950">SecureDocs AI Hub</h1>
      <p className="mt-2 text-xs text-slate-500">역할 기반 메뉴는 편의 UI이며 백엔드 권한 검사를 대체하지 않습니다.</p>
      <nav className="mt-8 space-y-2">
        {visibleItems.map((item) => (
          <Link className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" href={item.href} key={item.href}>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
