"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, hasToken, setToken } from "@/lib/api";

interface Session {
  userId: string;
  role: string;
  fullName: string;
}

interface AuthContextValue {
  session: Session | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem("mcp_guardid_session") : null;
    if (raw && hasToken()) {
      setSession(JSON.parse(raw));
    }
    setLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const res = await api.login(email, password);
    setToken(res.access_token);
    const s: Session = { userId: res.user_id, role: res.role, fullName: res.full_name };
    window.localStorage.setItem("mcp_guardid_session", JSON.stringify(s));
    setSession(s);
    router.push("/");
  }

  async function register(email: string, fullName: string, password: string) {
    const res = await api.register(email, fullName, password);
    setToken(res.access_token);
    const s: Session = { userId: res.user_id, role: res.role, fullName: res.full_name };
    window.localStorage.setItem("mcp_guardid_session", JSON.stringify(s));
    setSession(s);
    router.push("/");
  }

  function logout() {
    clearToken();
    window.localStorage.removeItem("mcp_guardid_session");
    setSession(null);
    router.push("/login");
  }

  return <AuthContext.Provider value={{ session, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
