import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  return (
    <div className="app-shell">
      {/* Priority 8 (design system): docs/design/ACCESSIBILITY.md's Skip
          Navigation requirement - hidden until focused, so keyboard
          users can jump past the sidebar/header on every page. */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <Sidebar />
      <div className="app-main">
        <Header />
        <main id="main-content" className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
