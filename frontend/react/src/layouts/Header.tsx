import { useAuth } from "../hooks/useAuth";

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="app-header">
      <span className="app-header-title">Scout</span>
      <div className="app-header-user">
        {user && <span>{user.email}</span>}
        <button type="button" onClick={logout}>
          Log out
        </button>
      </div>
    </header>
  );
}
