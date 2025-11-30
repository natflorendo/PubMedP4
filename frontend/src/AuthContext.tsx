/**
 * AuthContext.tsx 
 *  
 */ 

import { createContext, useContext, useEffect, useState } from "react";
import { AuthResponse, User } from "./types";
import { me } from "./api";

type AuthContextType = {
  user: User | null;
  token: string | null;
  setAuth: (auth: AuthResponse) => void;
  logout: () => void;
  loading: boolean;
};

// React context that stores authentication state for the app.
// createContext + <AuthContext.Provider> allows descendents to get the auth state with useAuth().
const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  setAuth: () => {},
  logout: () => {},
  loading: true,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true); // used for initial load

  useEffect(() => {
    loadUser();
  }, [token]);
  
  async function loadUser() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const current = await me();
        setUser(current);
      } catch {
        logout();
      } finally {
        setLoading(false);
      }
    }
    
  const setAuth = (auth: AuthResponse) => {
    localStorage.setItem("token", auth.access_token);
    setToken(auth.access_token);
    setUser(auth.user);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, setAuth, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}


export const useAuth = () => useContext(AuthContext);
