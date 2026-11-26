import React, { useEffect, useState } from 'react';
import {
  Users,
  Flame,
  PhoneCall,
  Calendar,
  TrendingUp,
  Award,
  Sparkles,
  ArrowRight,
  Smile,
  Meh,
  Frown,
  Clock,
  CheckCircle,
  FileText
} from 'lucide-react';
import { api } from '../services/api';

export default function DashboardView({ onNavigateToVoice, systemStatus }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const data = await api.getDashboardAnalytics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400">Loading CRM analytics...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Inbound Leads',
      value: metrics?.total_leads || 0,
      sub: `${metrics?.hot_leads || 0} Hot • ${metrics?.warm_leads || 0} Warm`,
      icon: Users,
      color: 'from-blue-500/20 to-indigo-500/20 text-blue-400 border-blue-500/30'
    },
    {
      title: 'High-Intent Hot Leads',
      value: metrics?.hot_leads || 0,
      sub: `${metrics?.total_leads ? Math.round((metrics.hot_leads / metrics.total_leads) * 100) : 0}% of pipeline`,
      icon: Flame,
      color: 'from-amber-500/20 to-red-500/20 text-amber-400 border-amber-500/30'
    },
    {
      title: 'Total Voice Conversations',
      value: metrics?.total_conversations || 0,
      sub: 'Automated sales interactions',
      icon: PhoneCall,
      color: 'from-emerald-500/20 to-teal-500/20 text-emerald-400 border-emerald-500/30'
    },
    {
      title: 'Upcoming Demos Booked',
      value: metrics?.upcoming_appointments || 0,
      sub: 'Verified scheduled calendar demos',
      icon: Calendar,
      color: 'from-purple-500/20 to-pink-500/20 text-purple-400 border-purple-500/30'
    },
    {
      title: 'Pipeline Conversion Rate',
      value: `${metrics?.conversion_rate || 0}%`,
      sub: 'Leads converted to demo/hot status',
      icon: TrendingUp,
      color: 'from-emerald-500/20 to-cyan-500/20 text-teal-400 border-teal-500/30'
    },
    {
      title: 'Average AI Lead Score',
      value: `${metrics?.average_lead_score || 0}/100`,
      sub: 'Across active opportunities',
      icon: Award,
      color: 'from-orange-500/20 to-amber-500/20 text-orange-400 border-orange-500/30'
    }
  ];

  const totalSentiment = (metrics?.sentiment_breakdown?.Positive || 0) +
    (metrics?.sentiment_breakdown?.Neutral || 0) +
    (metrics?.sentiment_breakdown?.Negative || 0) || 1;

  const posPct = Math.round(((metrics?.sentiment_breakdown?.Positive || 0) / totalSentiment) * 100);
  const neuPct = Math.round(((metrics?.sentiment_breakdown?.Neutral || 0) / totalSentiment) * 100);
  const negPct = Math.round(((metrics?.sentiment_breakdown?.Negative || 0) / totalSentiment) * 100);

  const engineMode = systemStatus?.active_engine || (systemStatus?.gemini?.mode === 'live' ? 'live_gemini' : 'local_demo');

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Dynamic Engine Status Banner */}
      {engineMode === 'live_gemini' && (
        <div className="p-3.5 px-5 rounded-xl bg-emerald-950/30 border border-emerald-500/30 flex items-center justify-between text-xs shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="font-bold text-emerald-400 uppercase tracking-wider">LIVE GEMINI AI ACTIVE</span>
            <span className="text-slate-400 hidden md:inline">• Primary provider with real-time generative reasoning and RAG</span>
          </div>
          <span className="text-slate-400 font-mono text-[11px]">Model: {systemStatus?.gemini?.model || 'gemini-3.8-flash'}</span>
        </div>
      )}
      {engineMode === 'live_groq' && (
        <div className="p-3.5 px-5 rounded-xl bg-purple-950/30 border border-purple-500/30 flex items-center justify-between text-xs shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping"></span>
            <span className="font-bold text-purple-400 uppercase tracking-wider">LIVE GROQ AI ACTIVE</span>
            <span className="text-slate-400 hidden md:inline">• Ultra-low latency LPU generative reasoning active</span>
          </div>
          <span className="text-purple-300 font-mono text-[11px] bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
            Model: {systemStatus?.groq?.model || 'llama-3.3-70b-versatile'}
          </span>
        </div>
      )}
      {engineMode !== 'live_gemini' && engineMode !== 'live_groq' && (
        <div className="p-3.5 px-5 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-center justify-between text-xs shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span className="font-bold text-amber-400 uppercase tracking-wider">LOCAL DEMO MODE (RELIABLE INTERVIEW ENGINE)</span>
            <span className="text-slate-300 hidden md:inline">• Voice sales dialogue, RAG knowledge, lead scoring & demo booking fully functional</span>
          </div>
          <span className="text-amber-400 font-mono text-[11px] bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
            Resilient Heuristic Fallback
          </span>
        </div>
      )}

      {/* Banner / Hero Action */}
      <div className="relative overflow-hidden rounded-2xl craft-card border-emerald-500/25 p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
        <div className="space-y-1.5 z-10">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 uppercase tracking-wider">
              Autonomous Sales AI
            </span>
            <span className="text-slate-400 text-xs">• Real-time RAG & Voice Synthesis</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            Meet FortiVoice AI Agent
          </h2>
          <p className="text-sm text-slate-300 max-w-xl">
            Simulate a live customer call. FortiVoice answers questions using enterprise company documents, scores customer readiness, and automatically books calendar appointments.
          </p>
        </div>
        <button
          onClick={onNavigateToVoice}
          className="z-10 py-3 px-6 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/25 transition-all duration-200 active:scale-95 shrink-0"
        >
          <Sparkles className="w-4 h-4 text-emerald-200" />
          <span>Launch AI Voice Session</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="p-5 rounded-2xl craft-card craft-card-interactive flex flex-col justify-between"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    {card.title}
                  </p>
                  <h3 className="text-3xl font-extrabold text-white mt-2 tracking-tight">
                    {card.value}
                  </h3>
                </div>
                <div className={`p-3 rounded-xl bg-gradient-to-br ${card.color} border`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <p className="text-xs text-slate-400 mt-4 font-medium">{card.sub}</p>
            </div>
          );
        })}
      </div>

      {/* Analytics Breakdown & Recent Activities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Analysis Breakdown */}
        <div className="p-6 rounded-2xl craft-card flex flex-col justify-between space-y-6">
          <div>
            <h4 className="text-base font-bold text-white tracking-tight">
              Customer Sentiment Analysis
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Live sentiment classification across conversations
            </p>
          </div>

          <div className="space-y-4">
            {/* Positive */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Smile className="w-4 h-4" />
                  <span>Positive Sentiment</span>
                </div>
                <span className="text-white">{posPct}% ({metrics?.sentiment_breakdown?.Positive || 0})</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-500"
                  style={{ width: `${posPct}%` }}
                ></div>
              </div>
            </div>

            {/* Neutral */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                <div className="flex items-center gap-2 text-blue-400">
                  <Meh className="w-4 h-4" />
                  <span>Neutral / Inquisitive</span>
                </div>
                <span className="text-white">{neuPct}% ({metrics?.sentiment_breakdown?.Neutral || 0})</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-indigo-400 rounded-full transition-all duration-500"
                  style={{ width: `${neuPct}%` }}
                ></div>
              </div>
            </div>

            {/* Negative */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
                <div className="flex items-center gap-2 text-rose-400">
                  <Frown className="w-4 h-4" />
                  <span>Objections / Hesitant</span>
                </div>
                <span className="text-white">{negPct}% ({metrics?.sentiment_breakdown?.Negative || 0})</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-rose-500 to-red-400 rounded-full transition-all duration-500"
                  style={{ width: `${negPct}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 text-xs text-slate-300">
            💡 Sentiment triggers dynamic agent tone adaptation during voice interactions.
          </div>
        </div>

        {/* Lead Quality Pipeline */}
        <div className="p-6 rounded-2xl craft-card flex flex-col justify-between space-y-6">
          <div>
            <h4 className="text-base font-bold text-white tracking-tight">
              Lead Qualification Tiers
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              AI scoring based on budget, urgency & engagement
            </p>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-white/[0.035] border border-amber-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-amber-400 animate-pulse"></div>
                <div>
                  <p className="text-sm font-bold text-white">HOT Leads (Score 75-100)</p>
                  <p className="text-xs text-slate-400">High budget, immediate timeline</p>
                </div>
              </div>
              <span className="text-xl font-extrabold text-amber-400">
                {metrics?.hot_leads || 0}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.035] border border-blue-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-blue-400"></div>
                <div>
                  <p className="text-sm font-bold text-white">WARM Leads (Score 40-74)</p>
                  <p className="text-xs text-slate-400">Evaluating solutions & pricing</p>
                </div>
              </div>
              <span className="text-xl font-extrabold text-blue-400">
                {metrics?.warm_leads || 0}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-white/[0.035] border border-white/[0.08] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-slate-400"></div>
                <div>
                  <p className="text-sm font-bold text-white">COLD Leads (Score 0-39)</p>
                  <p className="text-xs text-slate-400">Browsing or deferred timeline</p>
                </div>
              </div>
              <span className="text-xl font-extrabold text-slate-400">
                {metrics?.cold_leads || 0}
              </span>
            </div>
          </div>

          <div className="text-xs text-slate-400 text-center font-medium">
            AI scoring updates continuously with every spoken customer reply.
          </div>
        </div>

        {/* Recent Activities Log */}
        <div className="p-6 rounded-2xl craft-card flex flex-col justify-between space-y-4">
          <div>
            <h4 className="text-base font-bold text-white tracking-tight">
              Recent CRM Activities
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Live automated events log
            </p>
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[250px] pr-1">
            {metrics?.recent_activities && metrics.recent_activities.length > 0 ? (
              metrics.recent_activities.map((act, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 flex items-start gap-3"
                >
                  <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
                    {act.type === 'appointment_scheduled' ? (
                      <Calendar className="w-3.5 h-3.5" />
                    ) : act.type === 'call_completed' ? (
                      <PhoneCall className="w-3.5 h-3.5" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-white truncate">{act.title}</p>
                    <p className="text-[11px] text-slate-400 truncate">{act.subtitle}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No recent activities recorded yet.</p>
            )}
          </div>

          <button
            onClick={loadDashboard}
            className="w-full py-2 text-xs font-semibold text-slate-400 hover:text-white bg-slate-800/40 rounded-xl transition-all"
          >
            Refresh Metrics
          </button>
        </div>
      </div>
    </div>
  );
}
