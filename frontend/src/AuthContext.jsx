import { createContext, useContext, useState, useEffect } from 'react';
import { getMe } from './api';
import { getToken, setToken, clearToken, PERSIST_FLAG } from './utils/tokenStore';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Safety cleanup: older builds always wrote the token to
    // localStorage with no opt-in marker, which persisted across tab
    // close and let the next browser visitor inherit the previous
    // user's session. Tokens written by the new dual-storage scheme
    // carry PERSIST_FLAG when remember-me is on; legacy tokens don't.
    // Only purge unmarked persistent tokens — keep the legitimate
    // remember-me ones so the feature actually works across restarts.
    try {
      const ls = localStorage.getItem('token');
      const ss = sessionStorage.getItem('token');
      const persistFlag = localStorage.getItem(PERSIST_FLAG);
      if (ls && !ss && !persistFlag) {
        localStorage.removeItem('token');
      }
    } catch { /* storage disabled */ }

    const token = getToken();
    if (token) {
      getMe()
        .then((res) => setUser(res.data))
        .catch(() => clearToken())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  // remember=true -> persistent localStorage; otherwise sessionStorage
  // so the auth disappears when the tab closes (shared-browser safety).
  const login = (token, userData, { remember = false } = {}) => {
    setToken(token, { remember });
    setUser(userData);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
