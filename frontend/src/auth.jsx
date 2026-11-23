// Keeps track of who is logged in, for the whole app.
// Any page can call useAuth() to get { user, login, register, logout }.
import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while we check a saved token

  // On page load: if a token was saved earlier, ask the API who it belongs to.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => setToken(null)) // token expired or invalid
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const data = await api("/auth/login", { method: "POST", form: { username: email, password } });
    setToken(data.access_token);
    setUser(data.user);
  }

  async function register(fields) {
    const data = await api("/auth/register", { method: "POST", body: fields });
    setToken(data.access_token);
    setUser(data.user);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    // setUser lets the Edit Profile page update the name shown in the navbar
    <AuthContext.Provider value={{ user, setUser, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
