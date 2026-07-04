import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const authStore = readFileSync(new URL("../lib/auth-store.ts", import.meta.url), "utf8");
const apiClient = readFileSync(new URL("../lib/api-client.ts", import.meta.url), "utf8");
const sidebar = readFileSync(new URL("../components/sidebar.tsx", import.meta.url), "utf8");

assert(!/localStorage|sessionStorage/.test(`${authStore}\n${apiClient}`), "Access Token must not be stored in browser storage");
assert(apiClient.includes('credentials: "include"'), "API client must include HttpOnly refresh cookie credentials");
assert(apiClient.includes('!(body instanceof FormData)'), "FormData requests must not force JSON Content-Type");
assert(apiClient.includes("let refreshPromise"), "API client must share one refresh promise for concurrent 401 responses");
assert(sidebar.includes("adminOnly") && sidebar.includes("isSystemAdmin"), "Sidebar must hide admin menu items for non-admin users");
