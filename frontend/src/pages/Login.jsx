import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Command, LockKeyhole, Mail } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError('System authentication failed');
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#030712] flex items-center justify-center overflow-hidden p-6 font-sans">
      
      {/* Breathtaking Background Glows */}
      <div className="absolute top-[10%] left-[-10%] w-[60%] h-[60%] bg-blue-600/20 rounded-full blur-[120px] -z-10 mix-blend-screen pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-indigo-600/20 rounded-full blur-[120px] -z-10 mix-blend-screen pointer-events-none"></div>

      <div className="w-full max-w-md animate-enter">
        <div className="glass-card p-8 md:p-10 rounded-[2rem] relative overflow-hidden">
          
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/[0.02] rounded-full blur-2xl transform translate-x-12 -translate-y-12"></div>
          
          <div className="flex flex-col items-center mb-10 relative z-10">
            <div className="w-16 h-16 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-blue-500/30 ring-1 ring-white/20 transform rotate-3 hover:rotate-0 transition-all duration-300">
              <Command className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">NEXUS Core</h1>
            <p className="text-slate-400 text-sm mt-2 font-medium">Authorized personnel only.</p>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl mb-6 text-sm text-center font-medium backdrop-blur-md flex items-center justify-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6 relative z-10">
            <div className="space-y-4">
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                  <Mail className="h-5 w-5" />
                </div>
                <input 
                  type="text" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-11 bg-black/40 border border-white/10 rounded-xl py-3.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all sm:text-sm backdrop-blur-md"
                  placeholder="operator@security.local"
                />
              </div>

              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <input 
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-11 bg-black/40 border border-white/10 rounded-xl py-3.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all sm:text-sm backdrop-blur-md"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={loading}
              className="w-full relative flex justify-center py-4 px-4 border border-transparent rounded-xl text-sm font-bold text-white bg-white/10 hover:bg-white/20 uppercase tracking-widest overflow-hidden transition-all group disabled:opacity-50"
            >
              <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-blue-600 to-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <span className="relative z-10 flex items-center gap-2 drop-shadow-md">
                {loading ? 'Authenticating...' : 'Initialize Session'}
              </span>
            </button>
          </form>
          
          <div className="mt-8 text-center relative z-10">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest">End-to-End Encrypted Node</p>
          </div>
        </div>
      </div>
    </div>
  );
}
