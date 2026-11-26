import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Key,
  Database,
  Cpu,
  Volume2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Layers,
  Zap,
  ShieldAlert
} from 'lucide-react';
import { api } from '../services/api';

export default function SettingsView({ language, setLanguage }) {
  const [settingsData, setSettingsData] = useState(null);
  
  // AI Provider mode
  const [aiProvider, setAiProvider] = useState('auto');
  
  // Gemini inputs
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [selectedGeminiModel, setSelectedGeminiModel] = useState('gemini-3.8-flash');
  const [testingGemini, setTestingGemini] = useState(false);
  const [geminiTestResult, setGeminiTestResult] = useState(null);

  // Groq inputs
  const [groqKeyInput, setGroqKeyInput] = useState('');
  const [selectedGroqModel, setSelectedGroqModel] = useState('qwen/qwen3.8-27b');
  const [testingGroq, setTestingGroq] = useState(false);
  const [groqTestResult, setGroqTestResult] = useState(null);

  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettingsData(data);
      if (data.ai_provider) setAiProvider(data.ai_provider);
      if (data.gemini?.model) setSelectedGeminiModel(data.gemini.model);
      if (data.groq?.model) setSelectedGroqModel(data.groq.model);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const handleSaveAll = async (e) => {
    e.preventDefault();
    try {
      await api.updateSettings({
        ai_provider: aiProvider,
        gemini_api_key: geminiKeyInput.trim() || undefined,
        gemini_model: selectedGeminiModel,
        groq_api_key: groqKeyInput.trim() || undefined,
        groq_model: selectedGroqModel
      });
      setSavedSuccess(true);
      setGeminiKeyInput('');
      setGroqKeyInput('');
      setTimeout(() => setSavedSuccess(false), 3000);
      loadSettings();
    } catch (err) {
      alert(err.message || 'Failed to update settings');
    }
  };

  const handleTestGemini = async () => {
    try {
      setTestingGemini(true);
      setGeminiTestResult(null);
      const res = await api.testGemini({
        api_key: geminiKeyInput.trim() || undefined,
        model: selectedGeminiModel
      });
      setGeminiTestResult(res);
      if (res.success) {
        loadSettings();
      }
    } catch (err) {
      setGeminiTestResult({ success: false, error: err.message });
    } finally {
      setTestingGemini(false);
    }
  };

  const handleTestGroq = async () => {
    try {
      setTestingGroq(true);
      setGroqTestResult(null);
      const res = await api.testGroq({
        api_key: groqKeyInput.trim() || undefined,
        model: selectedGroqModel
      });
      setGroqTestResult(res);
      if (res.success) {
        loadSettings();
      }
    } catch (err) {
      setGroqTestResult({ success: false, error: err.message });
    } finally {
      setTestingGroq(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h3 className="text-xl font-bold text-white tracking-tight">System Configuration & Security</h3>
        <p className="text-xs text-slate-400">
          Manage Automatic Gemini → Groq → Local Demo fallback architecture, credentials, and persistent data
        </p>
      </div>

      {/* Fallback Architecture Overview Card */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-900/90 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-emerald-400" />
            <h4 className="text-base font-bold text-white">Multi-Provider AI Fallback Architecture</h4>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Active Routing:</span>
            <select
              value={aiProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1 text-xs font-semibold text-emerald-400 focus:outline-none"
            >
              <option value="auto">Auto (Gemini → Groq → Local Demo)</option>
              <option value="gemini">Gemini Only (Primary)</option>
              <option value="groq">Groq Only (Secondary)</option>
              <option value="local">Local Demo Engine Only (Offline)</option>
            </select>
          </div>
        </div>

        {/* 3-Step Cascade Visualizer */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs">
          <div className={`p-3.5 rounded-xl border ${
            settingsData?.gemini?.is_configured && !settingsData?.gemini?.is_quota_exhausted
              ? 'bg-emerald-950/20 border-emerald-500/30'
              : 'bg-slate-800/40 border-slate-800'
          }`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-slate-200">1. PRIMARY</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                settingsData?.gemini?.is_configured && !settingsData?.gemini?.is_quota_exhausted
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {settingsData?.gemini?.is_configured ? (settingsData.gemini.is_quota_exhausted ? '429 Quota Hit' : 'Live') : 'No Key'}
              </span>
            </div>
            <p className="font-semibold text-white">Google Gemini AI</p>
            <p className="text-[11px] text-slate-400 mt-1">High-reasoning multimodal sales intelligence & RAG</p>
          </div>

          <div className={`p-3.5 rounded-xl border ${
            settingsData?.groq?.is_configured && !settingsData?.groq?.is_rate_limited
              ? 'bg-purple-950/20 border-purple-500/30'
              : 'bg-slate-800/40 border-slate-800'
          }`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-slate-200">2. SECONDARY</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                settingsData?.groq?.is_configured && !settingsData?.groq?.is_rate_limited
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {settingsData?.groq?.is_configured ? (settingsData.groq.is_rate_limited ? '429 Rate Hit' : 'Live') : 'Optional'}
              </span>
            </div>
            <p className="font-semibold text-white">Groq AI (Llama 3.3)</p>
            <p className="text-[11px] text-slate-400 mt-1">Ultra-low latency LPU automatic retry engine</p>
          </div>

          <div className="p-3.5 rounded-xl border bg-amber-950/20 border-amber-500/30">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-slate-200">3. FINAL FALLBACK</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400">
                100% Reliable
              </span>
            </div>
            <p className="font-semibold text-white">Local Demo Engine</p>
            <p className="text-[11px] text-slate-400 mt-1">Deterministic speech, lead scoring, and appointment booking</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSaveAll} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Google Gemini Card */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Key className="w-5 h-5 text-emerald-400" />
                  <h4 className="text-base font-bold text-white">Google Gemini AI</h4>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider border ${
                    settingsData?.gemini?.is_configured && !settingsData?.gemini?.is_quota_exhausted
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {settingsData?.gemini?.is_configured
                    ? (settingsData.gemini.is_quota_exhausted ? 'Quota Exceeded' : 'Connected')
                    : 'Unconfigured'}
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Primary model for contextual dialogue, qualification scoring, and executive summaries.
              </p>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Gemini API Key
                </label>
                <input
                  type="password"
                  value={geminiKeyInput}
                  onChange={(e) => setGeminiKeyInput(e.target.value)}
                  placeholder={
                    settingsData?.gemini?.masked_key
                      ? `Current Key: ${settingsData.gemini.masked_key}`
                      : 'Paste your Google AI Studio API Key...'
                  }
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Gemini Model
                </label>
                <select
                  value={selectedGeminiModel}
                  onChange={(e) => setSelectedGeminiModel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="gemini-3.8-flash">Gemini 3.8 Flash (Active Current Google Model - Recommended)</option>
                  <option value="gemini-flash-latest">Gemini Flash Latest</option>
                  <option value="gemini-2.5-pro">Gemini 2.5 Pro (Deep Reasoning)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleTestGemini}
                  disabled={testingGemini}
                  className="py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all border border-slate-700"
                >
                  {testingGemini ? 'Testing...' : 'Test Gemini Connection'}
                </button>
                <a
                  href="https://aistudio.google.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:underline ml-auto"
                >
                  <span>Google AI Studio</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {geminiTestResult && (
                <div
                  className={`p-3 rounded-xl border text-xs ${
                    geminiTestResult.success
                      ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                      : 'bg-rose-950/30 border-rose-500/40 text-rose-300'
                  }`}
                >
                  {geminiTestResult.success
                    ? `✓ Live Gemini API Verified! Model: ${geminiTestResult.model}`
                    : `✗ ${geminiTestResult.error || geminiTestResult.message}`}
                </div>
              )}
            </div>
          </div>

          {/* Groq AI Card */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-purple-400" />
                  <h4 className="text-base font-bold text-white">Groq AI (Secondary Fallback)</h4>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider border ${
                    settingsData?.groq?.is_configured && !settingsData?.groq?.is_rate_limited
                      ? 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {settingsData?.groq?.is_configured
                    ? (settingsData.groq.is_rate_limited ? 'Rate Limited' : 'Connected')
                    : 'Optional'}
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Ultra-fast inference fallback. Automatically called when Gemini encounters 429 quota limits or temporary server errors.
              </p>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Groq API Key
                </label>
                <input
                  type="password"
                  value={groqKeyInput}
                  onChange={(e) => setGroqKeyInput(e.target.value)}
                  placeholder={
                    settingsData?.groq?.masked_key
                      ? `Current Key: ${settingsData.groq.masked_key}`
                      : 'gsk_... (Paste your Groq API Key)'
                  }
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Groq Model
                </label>
                <select
                  value={selectedGroqModel}
                  onChange={(e) => setSelectedGroqModel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="qwen/qwen3.8-27b">qwen/qwen3.8-27b (Verified Active & Ultra-Fast - Recommended)</option>
                  <option value="openai/gpt-oss-120b">openai/gpt-oss-120b (Deep Reasoning)</option>
                  <option value="openai/gpt-oss-20b">openai/gpt-oss-20b (Fast Response)</option>
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleTestGroq}
                  disabled={testingGroq}
                  className="py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all border border-slate-700"
                >
                  {testingGroq ? 'Testing...' : 'Test Groq Connection'}
                </button>
                <a
                  href="https://console.groq.com/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-purple-400 hover:underline ml-auto"
                >
                  <span>Groq Console</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {groqTestResult && (
                <div
                  className={`p-3 rounded-xl border text-xs ${
                    groqTestResult.success
                      ? 'bg-purple-950/30 border-purple-500/40 text-purple-300'
                      : 'bg-rose-950/30 border-rose-500/40 text-rose-300'
                  }`}
                >
                  {groqTestResult.success
                    ? `✓ Live Groq API Verified! Model: ${groqTestResult.model}`
                    : `✗ ${groqTestResult.error || groqTestResult.message}`}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Global Save Button */}
        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400">
            Keys are securely kept on backend and persisted to <code className="text-slate-300 font-mono">backend/.env</code>.
          </div>
          <div className="flex items-center gap-3">
            {savedSuccess && (
              <span className="text-xs text-emerald-400 font-semibold animate-pulse">
                ✓ All configuration saved successfully!
              </span>
            )}
            <button
              type="submit"
              className="py-2.5 px-6 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-xs shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </form>

      {/* Database & Vector Storage Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            <h4 className="text-base font-bold text-white">Database & Vector Storage</h4>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="font-bold text-white">CRM Database</p>
                <p className="text-slate-400 mt-0.5">{settingsData?.database?.type}</p>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-4 h-4" />
                <span>Healthy</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 flex items-center justify-between">
              <div>
                <p className="font-bold text-white">RAG Vector Database</p>
                <p className="text-slate-400 mt-0.5">{settingsData?.rag?.vector_store}</p>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-4 h-4" />
                <span>Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Speech Synthesis Options */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-emerald-400" />
            <h4 className="text-base font-bold text-white">Speech Synthesis Options</h4>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Default Language</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setLanguage('en')}
                  className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                    language === 'en'
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  English (US)
                </button>
                <button
                  onClick={() => setLanguage('hi')}
                  className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                    language === 'hi'
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  Hindi (हिन्दी)
                </button>
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              FortiVoice utilizes high-fidelity Web Speech Synthesis with automatic regional accent matching. Speech STT & TTS stay on the browser and are never routed through LLM APIs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
