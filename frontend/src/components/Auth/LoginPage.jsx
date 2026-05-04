import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import axios from 'axios';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/login', {
        email,
        password,
      }, { timeout: 10000 });

      const { token, role } = response.data;
      login(token, role, email);

      // Redirect based on role
      if (role === 'admin') navigate('/admin');
      else if (role === 'professor') navigate('/professor');
      else navigate('/student');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest relative overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-secondary-container/15 blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-md p-8 z-10">
        <div className="bg-surface-container-low/40 backdrop-blur-2xl border border-outline-variant/20 rounded-[2rem] p-8 shadow-2xl shadow-black/40">
          <div className="flex flex-col items-center mb-10">
            <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-primary/30">
              <span className="text-3xl text-on-primary font-bold">S</span>
            </div>
            <h1 className="text-3xl font-bold text-on-surface">SemSaver</h1>
            <p className="text-on-surface-variant text-sm mt-2">Sign in to your study workspace</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-on-surface-variant mb-2 ml-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-surface-container-high/50 border border-outline-variant/30 rounded-2xl px-5 py-4 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="student@semsaver.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-on-surface-variant mb-2 ml-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-surface-container-high/50 border border-outline-variant/30 rounded-2xl px-5 py-4 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="p-4 bg-error-container/20 border border-error/30 rounded-xl text-error text-sm animate-shake">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-primary/90 text-on-primary font-bold py-4 rounded-2xl transition-all transform active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin"></div>
                  <span>Signing in...</span>
                </div>
              ) : 'Sign In'}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-outline-variant/10 text-center">
            <p className="text-xs text-on-surface-variant/60 leading-relaxed">
              Default accounts for demo:<br/>
              student@semsaver.com / student123<br/>
              professor@semsaver.com / prof123
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
