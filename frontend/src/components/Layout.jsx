import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Camera, LayoutDashboard, Video, Search, LogOut, Bell, Command, UserCircle, ShieldAlert, Activity, Database } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const location = useLocation();
  const { logout, user } = useAuth();
  
  const navItems = [
    { label: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Live Monitor', path: '/live', icon: Activity },
    { label: 'Manage Cameras', path: '/cameras', icon: Camera },
    { label: 'Video Inference', path: '/video', icon: Video },
    { label: 'Investigation', path: '/search', icon: Search },
    { label: 'Watchlist', path: '/watchlist', icon: ShieldAlert },
    { label: 'View Records', path: '/records', icon: Database },
    { label: 'System Guide', path: '/guide', icon: BookOpen },
  ];

  return (
    <div className="flex h-[100dvh] bg-[#030712] text-slate-200 overflow-hidden selection:bg-blue-500/30 font-sans">
      
      {/* Premium Sidebar */}
      <aside className="hidden md:flex flex-col w-[280px] glass border-r z-50 transition-all duration-300">
        <div className="h-20 flex items-center px-8 border-b border-white/[0.05]">
          <Command className="w-8 h-8 text-blue-500 mr-3 animate-pulse" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">NEXUS</h1>
            <p className="text-[10px] text-blue-400 font-mono tracking-widest uppercase">AI Command Center</p>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto py-8 px-4 space-y-2">
          <p className="px-4 text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">Operations</p>
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link 
                key={item.path} 
                to={item.path}
                className={`flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-300 relative group overflow-hidden ${
                  active 
                    ? 'bg-blue-600/10 text-blue-400' 
                    : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-200'
                }`}
              >
                {active && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-r shadow-[0_0_10px_rgba(59,130,246,0.8)]"></div>
                )}
                <Icon className={`w-5 h-5 transition-transform duration-300 ${active ? 'scale-110' : 'group-hover:scale-110'}`} />
                <span className={`font-medium ${active ? 'text-white' : ''}`}>{item.label}</span>
              </Link>
            )
          })}
        </div>
        
        <div className="p-6 border-t border-white/[0.05]">
          <div className="flex items-center justify-between bg-white/[0.02] p-3 rounded-2xl border border-white/[0.05] hover:bg-white/[0.04] transition-colors cursor-pointer" onClick={logout}>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-tr from-blue-500 to-indigo-600 rounded-full shadow-lg shadow-blue-500/20">
                <UserCircle className="w-5 h-5 text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-white truncate max-w-[100px]">{user?.email?.split('@')[0] || 'Admin'}</span>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider">{user?.role || 'Operator'}</span>
              </div>
            </div>
            <LogOut className="w-5 h-5 text-slate-500 hover:text-red-400 transition-colors" />
          </div>
        </div>
      </aside>

      {/* Main Content wrapper */}
      <div className="flex-1 flex flex-col relative overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/10 via-[#030712] to-[#030712]">
        
        {/* Top Header */}
        <header className="h-20 glass border-b flex items-center justify-between px-8 z-40 shrink-0">
          <div className="flex items-center text-sm font-medium text-slate-400">
            <span className="text-blue-500 mr-2 uppercase tracking-widest text-[10px] sm:text-xs">System Network /</span> 
            <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.8)] animate-pulse"></div> Secure Connection</span>
          </div>
          <div className="flex items-center gap-6">
            <button className="relative text-slate-400 hover:text-white transition-colors group">
              <Bell className="w-6 h-6 group-hover:scale-110 transition-transform" />
              <div className="absolute top-0 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[#090e1a]"></div>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-8 relative z-10 scroll-smooth pb-24 md:pb-8">
          <div className="max-w-7xl mx-auto h-full animate-enter">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile Navbar */}
      <nav className="md:hidden glass fixed bottom-0 left-0 right-0 h-20 px-6 flex justify-around items-center z-50 border-t">
         {navItems.map((item) => {
            const active = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link 
                key={item.path} 
                to={item.path}
                className={`flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition-all ${
                  active ? 'bg-blue-600/20 text-blue-400' : 'text-slate-500'
                }`}
              >
                <Icon className={`w-6 h-6 mb-1 ${active ? 'shadow-blue-500 drop-shadow-[0_0_8px_rgba(59,130,246,0.8)]' : ''}`} />
                <span className="text-[9px] font-semibold tracking-wide">{item.label.split(' ')[0]}</span>
              </Link>
            )
          })}
      </nav>
    </div>
  );
}
