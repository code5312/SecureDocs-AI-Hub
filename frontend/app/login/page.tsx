"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError } from "../../lib/api-shared";
import { useAuthStore } from "../../lib/auth-store";

function getNextPath(): string {
  if (typeof window === "undefined") {
    return "/dashboard";
  }
  const next = new URLSearchParams(window.location.search).get("next");
  return next?.startsWith("/") ? next : "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const status = useAuthStore((state) => state.status);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(getNextPath());
    }
  }, [router, status]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace(getNextPath());
    } catch (caught) {
      if (caught instanceof ApiClientError && caught.status === 401) {
        setError("이메일 또는 비밀번호가 올바르지 않습니다.");
      } else if (caught instanceof ApiClientError) {
        setError(caught.message);
      } else {
        setError("네트워크 오류로 로그인할 수 없습니다.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="mx-auto max-w-md space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={submit}>
      <h1 className="text-2xl font-bold">로그인</h1>
      <p className="text-sm text-slate-500">Access Token은 메모리에만 저장하고 Refresh Token은 HttpOnly 쿠키로 유지합니다.</p>
      <label className="block text-sm font-medium">이메일<input className="mt-1 w-full rounded border p-2" value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required /></label>
      <label className="block text-sm font-medium">비밀번호<input className="mt-1 w-full rounded border p-2" value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></label>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      <button className="w-full rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isSubmitting || status === "loading"} type="submit">{isSubmitting ? "로그인 중..." : "로그인"}</button>
    </form>
  );
}
