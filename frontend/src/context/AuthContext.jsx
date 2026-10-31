import { createContext, useContext, useEffect, useMemo, useState } from "react";
import client from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await client.post("/api/auth/login", { email, password });
    localStorage.setItem("token", res.data.access_token);
    setUser({ email: res.data.email, name: res.data.name, role: res.data.role });
  };

  const register = async (payload) => {
    const res = await client.post("/api/auth/register", payload);
    localStorage.setItem("token", res.data.access_token);
    setUser({ email: res.data.email, name: res.data.name, role: res.data.role });
  };

  const logout = async () => {
    try {
      await client.post("/api/auth/logout");
    } catch {
      /* still clear local session */
    }
    localStorage.removeItem("token");
    setUser(null);
  };

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
