import type { Metadata } from "next";

import { Sidebar } from "../components/sidebar";
import { Topbar } from "../components/topbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureDocs AI Hub",
  description: "Enterprise document management and AI knowledge prototype",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar />
            <main className="flex-1 p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
