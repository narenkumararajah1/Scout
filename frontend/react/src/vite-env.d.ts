/// <reference types="vite/client" />

// Declared explicitly rather than relying on Vite's catch-all index
// signature, so a typo in a variable name is a compile error instead of
// a silently-undefined value at runtime. This is the first build-time
// setting the app reads; add new VITE_ variables here as they appear.
interface ImportMetaEnv {
  /** "true" to require login. Must match the backend's REQUIRE_AUTHENTICATION. */
  readonly VITE_REQUIRE_AUTH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
