// Holds client-side session state (V3 Phase 7A). Restores the session
// on load via GET /api/v1/auth/me if a token is already in
// localStorage; clears it whenever any request comes back 401 (see
// api/client.ts's authEvents). Split from AuthContext.ts so this file
// only exports the component - co-exporting the context object here
// too trips the project's react-refresh/only-export-components lint
// rule (.eslintrc.cjs).
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { authEvents, getStoredToken } from "../api/client";
import { authService } from "../services/authService";
import type { User } from "../types/auth";
import { AuthContext, type AuthContextValue } from "./AuthContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!getStoredToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authService.getCurrentUser();
        if (!cancelled) {
          setUser(currentUser);
        }
      } catch {
        authService.logout();
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      setUser(null);
    }
    authEvents.addEventListener("unauthorized", handleUnauthorized);
    return () => authEvents.removeEventListener("unauthorized", handleUnauthorized);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await authService.login(email, password);
    setUser(result.user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isAuthenticated: user !== null, isLoading, login, logout }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
