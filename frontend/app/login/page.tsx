"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost/api/v1";
    const response = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
      return;
    }
    router.push("/dashboard");
  }

  return (
    <form className="mx-auto max-w-md space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" onSubmit={submit}>
      <h1 className="text-2xl font-bold">로그인</h1>
      <label className="block text-sm font-medium">이메일<input className="mt-1 w-full rounded border p-2" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label>
      <label className="block text-sm font-medium">비밀번호<input className="mt-1 w-full rounded border p-2" value={password} onChange={(event) => setPassword(event.target.value)} type="password" required /></label>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      <button className="w-full rounded bg-slate-950 px-4 py-2 text-white disabled:opacity-60" disabled={isSubmitting} type="submit">{isSubmitting ? "로그인 중..." : "로그인"}</button>
    </form>
  );
}
