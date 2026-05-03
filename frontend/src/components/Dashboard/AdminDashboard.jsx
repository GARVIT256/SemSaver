import React from 'react';

const AdminDashboard = () => {
  const metrics = [
    { label: 'Total Users', value: '142.8k', trend: '+12.4%', icon: 'group', color: 'primary' },
    { label: 'Queries Processed', value: '8.4M', trend: '+4.2%', icon: 'database', color: 'secondary' },
    { label: 'Active Sessions', value: '3,204', trend: '-1.1%', icon: 'memory', color: 'tertiary' },
  ];

  return (
    <div className="flex-1 p-8 pt-24 max-w-[1280px] mx-auto w-full flex flex-col gap-8">
      {/* Page Header */}
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2 font-inter tracking-tight">Telemetry & Health</h1>
          <p className="text-on-surface-variant font-body-base">Real-time system monitoring for SemSaver AI infrastructure.</p>
        </div>
        <div className="flex items-center gap-2 bg-surface-container-low/50 px-4 py-2 rounded-full border border-white/5">
          <div className="w-2 h-2 rounded-full bg-tertiary-container animate-pulse shadow-[0_0_10px_rgba(220,137,0,0.8)]"></div>
          <span className="font-mono text-xs text-tertiary uppercase tracking-widest font-bold">System Nominal</span>
        </div>
      </header>

      {/* Metrics Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {metrics.map((m, i) => (
          <div key={i} className="glass-panel rounded-xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:opacity-40 transition-opacity">
              <span className={`material-symbols-outlined text-5xl text-${m.color}`}>{m.icon}</span>
            </div>
            <h3 className="text-[11px] font-bold text-on-surface-variant mb-4 uppercase tracking-widest">{m.label}</h3>
            <div className="flex items-baseline gap-3">
              <span className={`text-4xl font-bold text-white glow-text-${m.color}`}>{m.value}</span>
              <div className={`flex items-center ${m.trend.startsWith('+') ? 'text-tertiary' : 'text-error'} font-mono text-xs font-bold`}>
                <span className="material-symbols-outlined text-[16px]">{m.trend.startsWith('+') ? 'trending_up' : 'trending_down'}</span>
                <span>{m.trend}</span>
              </div>
            </div>
            <div className="mt-4 h-1 w-full bg-white/5 rounded-full overflow-hidden">
              <div 
                className={`h-full bg-${m.color} shadow-[0_0_10px_rgba(166,200,255,0.8)]`}
                style={{ width: i === 0 ? '78%' : i === 1 ? '92%' : '65%' }}
              ></div>
            </div>
          </div>
        ))}
      </section>

      {/* Middle Row: Chart & Logs */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[400px]">
        {/* API Usage Chart */}
        <div className="lg:col-span-2 glass-panel rounded-xl p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-white">API Throughput</h3>
            <div className="flex gap-2">
              <button className="px-3 py-1 rounded-md bg-white/5 text-[10px] font-bold text-on-surface-variant hover:text-white transition-colors uppercase tracking-widest">1H</button>
              <button className="px-3 py-1 rounded-md bg-primary/20 text-primary border border-primary/30 text-[10px] font-bold shadow-[0_0_10px_rgba(166,200,255,0.2)] uppercase tracking-widest">24H</button>
              <button className="px-3 py-1 rounded-md bg-white/5 text-[10px] font-bold text-on-surface-variant hover:text-white transition-colors uppercase tracking-widest">7D</button>
            </div>
          </div>
          
          <div className="flex-1 flex items-end gap-2 mt-4 relative">
            <div className="flex-1 flex items-end justify-between pl-8 pb-6 h-full z-10">
              {[40, 65, 50, 90, 75, 45, 60].map((h, i) => (
                <div 
                  key={i}
                  className={`w-8 rounded-t-sm transition-all duration-1000 ${i === 3 ? 'bg-gradient-to-t from-secondary/20 to-secondary/80 shadow-[0_0_15px_rgba(202,190,255,0.4)]' : 'bg-gradient-to-t from-primary/20 to-primary/80'}`}
                  style={{ height: `${h}%` }}
                >
                  {i === 3 && (
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-surface-container border border-white/10 px-2 py-1 rounded text-[10px] font-mono text-white">8.2k</div>
                  )}
                </div>
              ))}
            </div>
            {/* Axis placeholders */}
            <div className="absolute bottom-0 left-8 right-0 flex justify-between text-on-surface-variant font-mono text-[10px] uppercase tracking-widest">
              <span>00:00</span>
              <span>12:00</span>
              <span>Now</span>
            </div>
          </div>
        </div>

        {/* Live Logs Panel */}
        <div className="glass-panel rounded-xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5 flex justify-between items-center bg-surface-container-low/50">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-tertiary">terminal</span>
              <h3 className="text-[11px] font-bold text-white uppercase tracking-widest">Live Stream</h3>
            </div>
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-white/20"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-white/20"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-tertiary shadow-[0_0_8px_rgba(255,184,102,0.8)]"></div>
            </div>
          </div>
          <div className="flex-1 terminal-log p-4 overflow-y-auto text-[11px] flex flex-col gap-2 font-mono">
            <div className="text-on-surface-variant"><span className="text-secondary mr-2">[14:02:01]</span> INFO: Worker node spin-up complete</div>
            <div className="text-on-surface-variant"><span className="text-secondary mr-2">[14:02:05]</span> DATA: Syncing semantic index shards...</div>
            <div className="text-primary glow-text-primary"><span className="text-secondary mr-2">[14:02:06]</span> SUCCESS: Index synced in 452ms</div>
            <div className="text-on-surface-variant"><span className="text-secondary mr-2">[14:02:12]</span> REQ: GET /api/v2/embeddings - 200 OK</div>
            <div className="text-tertiary"><span className="text-secondary mr-2">[14:02:18]</span> WARN: Latency spike detected (850ms)</div>
            <div className="text-primary glow-text-primary"><span className="text-secondary mr-2">[14:02:30]</span> SUCCESS: DB failover successful.</div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;
