import { create } from "zustand";
import { api } from "../api/client";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("token"),

  login: async (email, password) => {
    const { data } = await api.post("/auth/login/json", { email, password });
    localStorage.setItem("token", data.access_token);
    set({ token: data.access_token });
    const me = await api.get("/auth/me");
    set({ user: me.data });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ user: null, token: null });
  },

  fetchMe: async () => {
    try {
      const { data } = await api.get("/auth/me");
      set({ user: data });
    } catch {
      set({ user: null, token: null });
      localStorage.removeItem("token");
    }
  },
}));
