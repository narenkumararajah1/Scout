import { UserMenu } from "../components/ui/UserMenu";
import { useAuth } from "../hooks/useAuth";

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="app-header">
      <span className="app-header-title">Scout</span>
      {user && <UserMenu user={user} onLogout={logout} />}
    </header>
  );
}
