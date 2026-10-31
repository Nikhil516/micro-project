import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const { push } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email.includes("@") || password.length < 8) {
      setError("Enter a valid email and a password of at least 8 characters.");
      return;
    }
    try {
      await login(email, password);
    } catch {
      setError("Invalid credentials.");
      push("Login failed", "error");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={onSubmit} className="card w-full max-w-md p-8">
        <p className="font-display text-4xl">Atelier Forecast</p>
        <p className="mt-2 text-stone-500">Sign in to the demand workspace.</p>
        <label className="mt-6 block text-sm">Email</label>
        <input className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} />
        <label className="mt-4 block text-sm">Password</label>
        <input type="password" className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error ? <p className="mt-3 text-sm text-rose-800">{error}</p> : null}
        <button className="mt-6 w-full rounded-lg bg-stone-900 py-2.5 text-white">Sign in</button>
        <p className="mt-4 text-sm text-stone-500">
          No account? <Link className="text-rose-800" to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
