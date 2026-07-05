"use client";

import { useEffect, type ReactNode } from "react";

import { useAuthStore } from "../lib/auth-store";

export function AuthProvider({ children }: { children: ReactNode }) {
  const restoreSession = useAuthStore((state) => state.restoreSession);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  return children;
}
