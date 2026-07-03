const navigationItems = [
  "대시보드",
  "문서 목록",
  "문서 업로드",
  "통합 검색",
  "AI 채팅",
  "지식 추천",
  "전문가 추천",
  "사용자 관리",
  "카테고리 관리",
  "백업 관리",
  "감사 로그",
];

export function Sidebar() {
  return (
    <aside className="hidden min-h-screen w-64 border-r border-slate-200 bg-white p-6 lg:block">
      <h1 className="text-lg font-bold text-slate-950">SecureDocs AI Hub</h1>
      <nav className="mt-8 space-y-2">
        {navigationItems.map((item) => (
          <a className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" href="#" key={item}>
            {item}
          </a>
        ))}
      </nav>
    </aside>
  );
}
