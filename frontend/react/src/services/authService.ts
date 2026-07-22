// Auth domain operations (V3 Phase 7A). Wraps /api/v1/auth/* - never
// duplicates backend/services/auth_service.py's logic, just calls it.
import { apiRequestData, clearStoredToken, getStoredToken, setStoredToken } from "../api/client";
import type { LoginResult, User } from "../types/auth";

export const authService = {
  async login(email: string, password: string): Promise<LoginResult> {
    const result = await apiRequestData<LoginResult>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    setStoredToken(result.access_token);
    return result;
  },

  async getCurrentUser(): Promise<User> {
    return apiRequestData<User>("/api/v1/auth/me");
  },

  logout(): void {
    clearStoredToken();
  },

  isAuthenticated(): boolean {
    return getStoredToken() !== null;
  },
};
