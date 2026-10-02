import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type TokenResponse, type User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role: string;
  phone?: string;
  organization_name?: string;
  profession?: string;
  specialty?: string;
  license_number?: string;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("sd_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("sd_token");
        localStorage.removeItem("sd_refresh");
      })
      .finally(() => setLoading(false));
  }, []);

  function persist(data: TokenResponse) {
    localStorage.setItem("sd_token", data.access_token);
    localStorage.setItem("sd_refresh", data.refresh_token);
    setUser(data.user);
  }

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      async login(email, password) {
        persist(await api.post<TokenResponse>("/auth/login", { email, password }));
      },
      async register(payload) {
        persist(await api.post<TokenResponse>("/auth/register", payload));
      },
      logout() {
        api.post("/auth/logout").catch(() => undefined);
        localStorage.removeItem("sd_token");
        localStorage.removeItem("sd_refresh");
        setUser(null);
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
