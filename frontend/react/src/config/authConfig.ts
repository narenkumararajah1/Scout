// Temporarily disables the login requirement (V2->V3 parity pass) so
// the app opens directly into the dashboard while a proper first-run/
// account experience is designed. Mirrors
// backend/config/settings.py's require_authentication flag - the
// backend already accepts requests with no token by default, so this
// only stops the frontend from redirecting to a login screen it
// doesn't need. Nothing about the auth system itself (LoginPage,
// AuthContext, authService, JWT issuance) is deleted - flip this back
// to true (and backend's require_authentication back to True) to
// restore it with no other code changes. See TECH_DEBT.md.
export const AUTH_REQUIRED = false;
