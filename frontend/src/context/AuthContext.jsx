import { createContext, useState, useEffect, useContext } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    const email = localStorage.getItem('email');
    if (token && email) {
      setUser({ token, email, role });
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    
    const { access_token } = response.data;
    
    // Decode token safely
    const payloadStart = access_token.indexOf('.') + 1;
    const payloadEnd = access_token.lastIndexOf('.');
    const payloadStr = atob(access_token.substring(payloadStart, payloadEnd));
    const payload = JSON.parse(payloadStr);
    
    localStorage.setItem('token', access_token);
    localStorage.setItem('role', payload.role);
    localStorage.setItem('email', payload.sub);
    setUser({ token: access_token, email: payload.sub, role: payload.role });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('email');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
