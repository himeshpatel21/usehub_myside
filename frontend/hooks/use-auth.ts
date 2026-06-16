"use client";

import { auth, type User } from "@/lib/api";
import { createContext, useContext, useEffect, useState } from "react";

interface AuthContext {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const AuthCtx = createContext<AuthContext>({
  user: null,
  loading: true,
  refresh: async () => {},
});

export function useAuth() {
  return useContext(AuthCtx);
}

export { AuthCtx };
