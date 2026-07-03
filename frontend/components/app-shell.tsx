"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AuthProvider } from "./auth-provider";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  return (
    <AuthProvider>
      <div className="flex min-h-screen">
        {isLogin ? null : <Sidebar />}
        <div className="flex min-w-0 flex-1 flex-col">
          {isLogin ? null : <Topbar />}
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
    </AuthProvider>
  );
}
