import React from 'react';
import {
  Mic,
  LayoutDashboard,
  Users,
  Calendar,
  PhoneCall,
  Database,
  Settings,
  Sparkles,
  Radio,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, systemStatus }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'voice-agent', label: 'AI Voice Agent', icon: Mic, badge: 'Live AI' },
    { id: 'leads', label: 'Leads Management', icon: Users },
    { id: 'appointments', label: 'Appointments', icon: Calendar },
    { id: 'calls', label: 'Call History', icon: PhoneCall },
    { id: 'knowledge-base', label: 'Knowledge Base', icon: Database },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0d1017]/90 backdrop-blur-xl border-r border-white/[0.06] shadow-[4px_0_30px_rgba(0,0,0,0.35)] flex flex-col shrink-0 min-h-screen relative z-20">
      {/* Brand Header */}
      <div className="p-6 border-b border-white/[0.06] flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 border border-white/10">
          <Sparkles className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <h1 className="font-extrabold text-lg text-white tracking-tight">FORTIVOICE</h1>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">Autonomous Sales AI & CRM</p>
        </div>
      </div>

      {/* Primary CTA */}
      <div className="p-4">
        <button
          onClick={() => setActiveTab('voice-agent')}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-[0_4px_20px_-2px_rgba(16,185,129,0.35),inset_0_1px_0_rgba(255,255,255,0.2)] transition-all duration-200 active:scale-95 border border-emerald-400/20"
        >
          <Radio className="w-4 h-4 animate-pulse text-emerald-200" />
          <span>Launch Voice Call</span>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-white/[0.08] text-emerald-400 font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_2px_10px_rgba(0,0,0,0.3)] border border-white/[0.08]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* System Status Footer */}
      <div className="p-4 border-t border-white/[0.06] bg-black/25">
        <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
          System Engine
        </div>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between text-slate-300">
            <span className="text-slate-400">AI Engine</span>
            <div className="flex items-center gap-1.5">
              {systemStatus?.active_engine === 'live_gemini' || (systemStatus?.gemini?.mode === 'live' && !systemStatus?.active_engine) ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  <span className="text-emerald-400 font-medium">Live Gemini</span>
                </>
              ) : systemStatus?.active_engine === 'live_groq' ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
                  <span className="text-purple-400 font-medium">Live Groq</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                  <span className="text-amber-400 font-medium">Demo Mode</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Routing</span>
            <span className="font-mono text-slate-300 uppercase">
              {systemStatus?.ai_provider || 'auto'}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-300">
            <span className="text-slate-400">Database</span>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="text-slate-300 font-medium">
                {systemStatus?.database?.is_live_mongo ? 'MongoDB' : 'Persistent DB'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
