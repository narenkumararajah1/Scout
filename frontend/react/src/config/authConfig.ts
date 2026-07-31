// Whether the app should require a login before rendering any page.
//
// **This must agree with the backend's REQUIRE_AUTHENTICATION.** They are
// separate switches doing different jobs - the backend decides what it
// answers, this decides whether the user is sent to a login screen - and
// disagreement is user-visible in both directions:
//
//   backend on, frontend off -> the dashboard renders, then every request
//       comes back 401, so the user sees a page full of errors instead of
//       the login form that would have fixed it.
//   backend off, frontend on -> a login screen guarding nothing.
//
// Read from the environment rather than hardcoded, so one deployment
// setting drives both. Defaults to off so local development still opens
// straight into the dashboard with no configuration.
//
// Set in the frontend's .env (or the build environment) as:
//   VITE_REQUIRE_AUTH=true
export const AUTH_REQUIRED = import.meta.env.VITE_REQUIRE_AUTH === "true";
