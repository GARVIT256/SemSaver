import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();

  const menuItems = [
    { name: 'Study Hub', icon: 'bolt', path: '/student', role: 'student' },
    { name: 'Professor Portal', icon: 'school', path: '/professor', role: 'professor' },
    { name: 'Data Lab', icon: 'insights', path: '/admin', role: 'admin' },
    { name: 'Archives', icon: 'inventory_2', path: '/archives', role: 'student' },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="fixed left-6 top-20 bottom-6 w-64 rounded-2xl border border-white/10 bg-slate-950/20 backdrop-blur-[40px] flex flex-col gap-2 p-4 h-[calc(100vh-104px)] shadow-2xl shadow-blue-500/5 z-40 divide-y divide-white/5 font-inter text-sm font-medium tracking-wide">
      {/* Header */}
      <div className="px-2 py-4 pb-6 flex items-center gap-3 border-b border-white/5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-container to-secondary-container p-[1px] shadow-lg shadow-primary/20">
          <div className="w-full h-full rounded-xl bg-surface-container flex items-center justify-center">
            <span className="material-symbols-outlined text-white">neurology</span>
          </div>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">SemSaver Pro</h1>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.6)]"></span>
            <span className="text-[11px] text-on-surface-variant uppercase tracking-widest font-semibold">AI Engine Active</span>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="pt-4 pb-2">
        <button className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-primary to-secondary-container text-white font-semibold text-sm hover:opacity-90 hover:shadow-[0_0_15px_rgba(166,200,255,0.3)] transition-all">
          <span className="material-symbols-outlined text-[18px]">add</span>
          New Session
        </button>
      </div>

      {/* Main Tabs */}
      <div className="flex-1 py-2 flex flex-col gap-1">
        {menuItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-300 border-l-2 ${
              isActive(item.path)
                ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/10 text-blue-300 border-blue-400 shadow-[0_0_15px_rgba(79,157,255,0.1)]'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5 hover:translate-x-1 border-transparent'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]" data-weight={isActive(item.path) ? "fill" : "normal"}>
              {item.icon}
            </span>
            <span>{item.name}</span>
          </Link>
        ))}
      </div>

      {/* Footer Tabs */}
      <div className="pt-2 flex flex-col gap-1 border-t border-white/5 mt-auto">
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 hover:translate-x-1 transition-all duration-300 border-l-2 border-transparent">
          <span className="material-symbols-outlined text-[20px]">help</span>
          <span>Help</span>
        </button>
        <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 hover:translate-x-1 transition-all duration-300 border-l-2 border-transparent">
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span>Sign Out</span>
        </button>
      </div>
    </nav>
  );
};

export default Sidebar;
