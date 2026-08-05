// The first screen anyone sees, so it carries the product's credibility
// before a single feature has been used.
//
// **The authentication path is untouched.** login(), the redirect, the
// error mapping and the submitting flag behave exactly as before; every
// change here is presentation, plus three accessibility fixes the
// original markup lacked (an announced error, an invalid state bound to
// the inputs, and a keyboard-reachable password reveal).
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getErrorMessage } from "../utils/errors";

// Inlined rather than pulled from an icon package: a handful of small
// glyphs does not justify a dependency on the one screen that has to
// render fastest, and these ship as part of the component's own markup.
function MailIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <rect x="2.6" y="4.4" width="14.8" height="11.2" rx="1.8" className="glyph-stroke" />
      <path d="m3.4 6 6.6 4.5L16.6 6" className="glyph-stroke" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5.6 8.8V6.9a4.4 4.4 0 0 1 8.8 0v1.9" className="glyph-stroke" />
      <rect x="3.9" y="8.8" width="12.2" height="7.8" rx="1.8" className="glyph-stroke" />
    </svg>
  );
}

function EyeIcon({ hidden }: { hidden: boolean }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M1.9 10S5 4.8 10 4.8 18.1 10 18.1 10 15 15.2 10 15.2 1.9 10 1.9 10Z" className="glyph-stroke" />
      <circle cx="10" cy="10" r="2.5" className="glyph-stroke" />
      {hidden && <path d="M3.6 3.6 16.4 16.4" className="glyph-stroke" />}
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="7.3" className="glyph-stroke" />
      <path d="M10 6.1v4.5M10 13.3v.3" className="glyph-stroke" />
    </svg>
  );
}

// Truthful to what Scout actually does. The grounding claim is the
// product's whole thesis, so overstating it on the very first screen
// would be the worst possible place to start.
const PROOF_POINTS = [
  "Researches companies from public sources and SEC filings",
  "Matches what it finds against work you have delivered",
  "Traces every recommendation back to a document",
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      {/* Decorative, and marked so: the gradient field carries no
          information and a screen reader announcing it is pure noise.
          It sits at page level rather than inside the brand panel so the
          light crosses the seam between the two columns - the halves read
          as one lit surface instead of two pages side by side. */}
      <div className="auth-aurora" aria-hidden="true" />

      <section className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-mark">
            <span className="auth-mark-glyph" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <circle cx="10.4" cy="10.4" r="6.3" className="glyph-stroke" />
                <path d="m15.2 15.2 4.4 4.4" className="glyph-stroke" />
              </svg>
            </span>
            <span className="auth-wordmark">Scout</span>
          </div>

          {/* Names the category in the headline and the differentiator in
              the same breath. "Research any company" described an action;
              this describes what Scout is. */}
          <p className="auth-tagline">
            Account intelligence, grounded in evidence.
          </p>
          <p className="auth-tagline-support">
            Scout researches the companies you sell to, matches what it finds against work you have
            already delivered, and traces every recommendation back to a document.
          </p>

          <ul className="auth-proof">
            {PROOF_POINTS.map((point) => (
              <li key={point}>
                <span className="auth-proof-tick" aria-hidden="true">
                  <svg viewBox="0 0 16 16" focusable="false">
                    <path d="m3.6 8.4 3 3 6.2-6.9" className="glyph-stroke" />
                  </svg>
                </span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <header className="auth-card-head">
            <p className="auth-eyebrow">Sign in</p>
            <h1 className="auth-heading">Welcome back</h1>
            <p className="auth-subheading">Enter your credentials to reach your workspace.</p>
          </header>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="login-email">Email</label>
              <div className="auth-input-shell">
                <span className="auth-input-icon" aria-hidden="true">
                  <MailIcon />
                </span>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="username"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  // Both fields carry the invalid state, because the API
                  // deliberately never says which credential was wrong.
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? "login-error" : undefined}
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="login-password">Password</label>
              <div className="auth-input-shell">
                <span className="auth-input-icon" aria-hidden="true">
                  <LockIcon />
                </span>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? "login-error" : undefined}
                  required
                />
                {/* A real button rather than a clickable icon, so it is
                    reachable by keyboard and announces its own state. */}
                <button
                  type="button"
                  className="auth-reveal"
                  onClick={() => setShowPassword((shown) => !shown)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                >
                  <EyeIcon hidden={showPassword} />
                </button>
              </div>
            </div>

            {/* role="alert" so it is announced the moment it appears. The
                original rendered a bare <p> that no screen reader would
                surface at all. */}
            {error && (
              <p className="auth-error" id="login-error" role="alert">
                <span className="auth-error-icon" aria-hidden="true">
                  <AlertIcon />
                </span>
                <span>{error}</span>
              </p>
            )}

            <button type="submit" className="auth-submit" disabled={isSubmitting}>
              {isSubmitting && <span className="auth-spinner" aria-hidden="true" />}
              {isSubmitting ? "Signing in" : "Sign in"}
            </button>
          </form>

          <footer className="auth-footer">
            <span className="auth-footer-note">
              <span className="auth-dot" aria-hidden="true" />
              Single-user workspace
            </span>
            <span className="auth-footer-meta">Scout v{__APP_VERSION__}</span>
          </footer>
        </div>
      </section>
    </div>
  );
}
