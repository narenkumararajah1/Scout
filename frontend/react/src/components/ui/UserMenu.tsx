// Account controls, relocated out of page content into a single
// top-right profile menu (GitHub/Notion/Jira-style). Menu items are
// data-driven so future entries (Profile, Preferences, Help, About)
// are a one-line addition rather than new markup.
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { User } from "../../types/auth";

interface UserMenuItem {
  label: string;
  to?: string;
  onSelect?: () => void;
}

interface UserMenuProps {
  user: User;
  onLogout: () => void;
}

function initialsFor(user: User): string {
  return user.email.charAt(0).toUpperCase();
}

export function UserMenu({ user, onLogout }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const items: UserMenuItem[] = [
    { label: "Settings", to: "/settings" },
    { label: "Log out", onSelect: onLogout },
  ];

  return (
    <div className="user-menu" ref={containerRef}>
      <button
        type="button"
        className="user-menu-trigger"
        onClick={() => setIsOpen((open) => !open)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <span className="user-menu-avatar">{initialsFor(user)}</span>
      </button>

      {isOpen && (
        <div className="user-menu-dropdown" role="menu">
          <div className="user-menu-dropdown-header">{user.email}</div>
          <div className="user-menu-dropdown-items">
            {items.map((item) =>
              item.to ? (
                <Link
                  key={item.label}
                  to={item.to}
                  className="user-menu-item"
                  role="menuitem"
                  onClick={() => setIsOpen(false)}
                >
                  {item.label}
                </Link>
              ) : (
                <button
                  key={item.label}
                  type="button"
                  className="user-menu-item"
                  role="menuitem"
                  onClick={() => {
                    setIsOpen(false);
                    item.onSelect?.();
                  }}
                >
                  {item.label}
                </button>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
