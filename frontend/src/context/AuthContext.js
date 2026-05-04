import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('semsaver_token');
    const role = localStorage.getItem('semsaver_role');
    const email = localStorage.getItem('semsaver_email');

    if (token && role) {
      setUser({ token, role, email });
    }
    setLoading(false);
  }, []);

  const login = (token, role, email) => {
    localStorage.setItem('semsaver_token', token);
    localStorage.setItem('semsaver_role', role);
    localStorage.setItem('semsaver_email', email);
    setUser({ token, role, email });
  };

  const logout = () => {
    localStorage.removeItem('semsaver_token');
    localStorage.removeItem('semsaver_role');
    localStorage.removeItem('semsaver_email');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
