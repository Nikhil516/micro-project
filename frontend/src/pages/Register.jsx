import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Register() {
  const { user, register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (form.name.length < 2 || !form.email.includes("@") || form.password.length < 8) {
      setError("Name, valid email, and password (8+ characters) are required.");
      return;
    }
    try {
      await register(form);
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={onSubmit} className="card w-full max-w-md p-8">
        <p className="font-display text-4xl">Create workspace access</p>
        {["name", "email", "password"].map((k) => (
          <div key={k} className="mt-4">
            <label className="text-sm capitalize">{k}</label>
            <input
              type={k === "password" ? "password" : "text"}
              className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
              value={form[k]}
              onChange={(e) => setForm({ ...form, [k]: e.target.value })}
            />
          </div>
        ))}
        {error ? <p className="mt-3 text-sm text-rose-800">{error}</p> : null}
        <button className="mt-6 w-full rounded-lg bg-stone-900 py-2.5 text-white">Register</button>
        <p className="mt-4 text-sm">
          <Link to="/login" className="text-rose-800">Back to sign in</Link>
        </p>
      </form>
    </div>
  );
}
