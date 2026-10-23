import { useState } from "react";
import { apiRequest } from "../api/axios.js";

export default function Login({ onLogin, onRetry, serviceError }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const session = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onLogin(session.username);
    } catch (requestError) {
      setError(requestError.status === 401 ? "That username or password doesn’t match." : requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-glow" aria-hidden="true" />
      <section className="login-card" aria-labelledby="login-title">
        <a className="brand login-brand" href="/" aria-label="Sentinel home">
          <span className="brand-mark">S</span>
          <span><strong>SENTINEL</strong><small>RISK INTELLIGENCE</small></span>
        </a>
        <div className="login-kicker"><span className="connection-dot" /> SECURE ANALYST ACCESS</div>
        <h1 id="login-title">Welcome back</h1>
        <p className="login-subtitle">Sign in to your fraud intelligence workspace.</p>
        <form className="login-form" onSubmit={submit}>
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            autoComplete="username"
            autoFocus
            maxLength={128}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Enter your username"
            required
            value={username}
          />
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            autoComplete="current-password"
            maxLength={1024}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            required
            type="password"
            value={password}
          />
          {(error || serviceError) && <p className="login-error" role="alert">{error || serviceError}</p>}
          <button className="button button-primary login-submit" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in securely"}
          </button>
        </form>
        <div className="login-help">
          {serviceError ? (
            <button className="text-button" onClick={onRetry} type="button">Retry API connection</button>
          ) : (
            <span>For local development, use the one-time credentials printed in the backend terminal.</span>
          )}
        </div>
        <div className="login-footer"><span>PAYMENTS RISK PLATFORM</span><span>Protected session · 12 hour expiry</span></div>
      </section>
    </main>
  );
}
