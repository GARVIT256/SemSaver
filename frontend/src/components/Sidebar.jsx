import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const allItems = [
    { name: 'Study Hub', icon: 'bolt', path: '/student', roles: ['student', 'admin'] },
    { name: 'Professor Portal', icon: 'school', path: '/professor', roles: ['professor', 'admin'] },
    { name: 'Data Lab', icon: 'insights', path: '/admin', roles: ['admin'] },
  ];

  const menuItems = allItems.filter(item => item.roles.includes(user?.role));

  const isActive = (path) => location.pathname === path;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="fixed left-6 top-6 bottom-6 w-64 rounded-3xl border border-white/10 bg-slate-950/40 backdrop-blur-[40px] flex flex-col gap-2 p-4 h-[calc(100vh-48px)] shadow-2xl z-40 divide-y divide-white/5 font-inter text-sm font-medium tracking-wide transition-all duration-300">
      {/* Header */}
      <div className="px-2 py-4 pb-6 flex items-center gap-3 border-b border-white/5">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
          <span className="material-symbols-outlined text-on-primary">neurology</span>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">SemSaver</h1>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">{user?.role} Mode</span>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex-1 py-6 flex flex-col gap-1.5">
        {menuItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 ${
              isActive(item.path)
                ? 'bg-primary text-on-primary shadow-lg shadow-primary/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">
              {item.icon}
            </span>
            <span>{item.name}</span>
          </Link>
        ))}
      </div>

      {/* Footer / User Profile */}
      <div className="pt-4 flex flex-col gap-2 border-t border-white/5 mt-auto">
        <div className="px-3 py-3 mb-2 bg-white/5 rounded-2xl overflow-hidden">
          <p className="text-[10px] text-slate-500 uppercase tracking-tighter mb-1">Logged in as</p>
          <p className="text-xs text-slate-300 truncate font-mono">{user?.email}</p>
        </div>
        
        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-2xl text-red-400 hover:bg-red-500/10 transition-all duration-300"
        >
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span>Sign Out</span>
        </button>
      </div>
    </nav>
  );
};

export default Sidebar;
