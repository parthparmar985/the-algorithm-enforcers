import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { BookOpen, Camera, LayoutDashboard, Video, Search, LogOut, ArrowUpRight, ShieldAlert, Activity, Database, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Brand } from '../pages/Landing';

export default function Layout({ children }) {
  const location = useLocation();
  const { logout, user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
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
  const currentPage = navItems.find(item => item.path === location.pathname)?.label || 'Workspace';
  return (
    <div className="workspace">
      <a className="skip-link" href="#workspace-main">Skip to content</a>
      <header className="workspace-header"><Brand /><div className="workspace-header-label">INTELLIGENCE / <strong>{currentPage}</strong></div><Link className="workspace-help" to="/guide">System guide <ArrowUpRight size={16} /></Link><button className="mobile-menu-toggle" aria-expanded={menuOpen} aria-controls="workspace-sidebar" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</button></header>
      <div className="workspace-body">
        <aside className={`workspace-sidebar ${menuOpen ? 'is-open' : ''}`} id="workspace-sidebar">
          <div className="sidebar-caption">YOUR COMMAND CENTER</div>
          <nav aria-label="Workspace navigation">{navItems.map(({ label, path, icon: Icon }) => <Link key={path} to={path} onClick={() => setMenuOpen(false)} aria-current={location.pathname === path ? 'page' : undefined} className={location.pathname === path ? 'active' : ''}><Icon size={19} /><span>{label}</span>{location.pathname === path && <ArrowUpRight size={16} />}</Link>)}</nav>
          <div className="sidebar-note"><span>LESS NOISE.<br />MORE CLARITY.</span><p>Your operation, in focus.</p></div>
          <div className="workspace-account"><span className="account-avatar">{(user?.email || 'N').slice(0, 1).toUpperCase()}</span><div><strong>{user?.email?.split('@')[0] || 'Operator'}</strong><small>{user?.role || 'Operator'}</small></div><button onClick={logout} aria-label="Log out" title="Log out"><LogOut size={18} /></button></div>
        </aside>
        <main id="workspace-main" className="workspace-content"><div className="max-w-7xl mx-auto animate-enter">{children}</div></main>
      </div>
    </div>
  );
}
