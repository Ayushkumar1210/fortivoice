import React from 'react';
import { Mic, Globe, Bell, Sparkles, Cpu, Zap } from 'lucide-react';

export default function Header({ activeTab, language, setLanguage, onStartCall, systemStatus }) {
  const titles = {
    dashboard: 'Executive CRM Dashboard',
    'voice-agent': 'Autonomous AI Sales Voice Agent',
    leads: 'Leads & Deal Qualification Pipeline',
    appointments: 'Appointment Calendar & Demo Bookings',
    calls: 'Call Records & AI Executive Summaries',
    'knowledge-base': 'RAG Vector Knowledge Base',
    settings: 'System Configuration & API Keys',
  };

  const engineMode = systemStatus?.active_engine || (systemStatus?.gemini?.mode === 'live' ? 'live_gemini' : 'local_demo');

  return (
    <header className="h-16 border-b border-white/[0.06] bg-[#0d1017]/75 backdrop-blur-xl px-8 flex items-center justify-between sticky top-0 z-30 shadow-[0_4px_20px_rgba(0,0,0,0.25)]">
      <div>
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white tracking-tight">
            {titles[activeTab] || 'FortiVoice CRM'}
          </h2>
          {/* Prominent Multi-Provider Engine Mode Indicator */}
          {engineMode === 'live_gemini' && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span>LIVE GEMINI AI</span>
            </span>
          )}
          {engineMode === 'live_groq' && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30 shadow-sm">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
              <span>LIVE GROQ AI</span>
            </span>
          )}
          {engineMode !== 'live_gemini' && engineMode !== 'live_groq' && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 shadow-sm" title="Operating in quota-resilient local demo engine mode">
              <Zap className="w-3 h-3 text-amber-400" />
              <span>LOCAL DEMO MODE (Reliable Simulation)</span>
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400">
          Autonomous Enterprise AI Voice Agent & Sales Pipeline
        </p>
      </div>

      <div className="flex items-center gap-4">
        {/* Language Selector */}
        <div className="flex items-center bg-slate-800/80 rounded-xl p-1 border border-slate-700/60 text-xs font-semibold">
          <button
            onClick={() => setLanguage('en')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              language === 'en'
                ? 'bg-emerald-500 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🇺🇸 English
          </button>
          <button
            onClick={() => setLanguage('hi')}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              language === 'hi'
                ? 'bg-emerald-500 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🇮🇳 Hindi
          </button>
        </div>

        {/* Quick Voice Call Launcher */}
        {activeTab !== 'voice-agent' && (
          <button
            onClick={onStartCall}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700/80 text-emerald-400 border border-emerald-500/30 text-xs font-semibold transition-all shadow-sm"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Voice Agent</span>
          </button>
        )}
      </div>
    </header>
  );
}
