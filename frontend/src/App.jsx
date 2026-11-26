import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import VoiceAgentView from './components/VoiceAgentView';
import LeadsView from './components/LeadsView';
import AppointmentsView from './components/AppointmentsView';
import CallHistoryView from './components/CallHistoryView';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import SettingsView from './components/SettingsView';
import { api } from './services/api';
import { speechService } from './services/speechService';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [language, setLanguage] = useState('en');
  const [systemStatus, setSystemStatus] = useState(null);

  useEffect(() => {
    checkSystemStatus();
  }, []);

  const handleTabChange = (newTab) => {
    if (newTab !== 'voice-agent') {
      speechService.cancelSpeech();
      speechService.stopListening();
    }
    setActiveTab(newTab);
  };

  const checkSystemStatus = async () => {
    try {
      const data = await api.getSettings();
      setSystemStatus(data);
    } catch (e) {
      console.warn('Backend not yet reachable:', e);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden humanized-canvas text-slate-100 font-sans selection:bg-emerald-500 selection:text-white relative">
      {/* Tactile Fine-Grain Studio Paper Texture (Subtle Humanized Feel) */}
      <div className="pointer-events-none fixed inset-0 z-40 grain-overlay opacity-70 mix-blend-overlay"></div>

      {/* Atmospheric Warm Ambient Lighting (Linear/Stripe Studio Aesthetic) */}
      <div className="pointer-events-none fixed -top-40 -left-40 w-[34rem] h-[34rem] bg-amber-500/[0.06] rounded-full blur-[120px]"></div>
      <div className="pointer-events-none fixed top-1/4 -right-40 w-[38rem] h-[38rem] bg-emerald-500/[0.07] rounded-full blur-[140px]"></div>
      <div className="pointer-events-none fixed -bottom-40 left-1/3 w-[42rem] h-[42rem] bg-indigo-500/[0.05] rounded-full blur-[150px]"></div>

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        systemStatus={systemStatus}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        <Header
          activeTab={activeTab}
          language={language}
          setLanguage={setLanguage}
          onStartCall={() => handleTabChange('voice-agent')}
          systemStatus={systemStatus}
        />

        <main className="flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <DashboardView
              onNavigateToVoice={() => handleTabChange('voice-agent')}
              systemStatus={systemStatus}
            />
          )}
          {activeTab === 'voice-agent' && (
            <VoiceAgentView
              language={language}
              setLanguage={setLanguage}
              systemStatus={systemStatus}
              onSummaryCreated={() => {
                checkSystemStatus();
              }}
            />
          )}
          {activeTab === 'leads' && <LeadsView />}
          {activeTab === 'appointments' && <AppointmentsView />}
          {activeTab === 'calls' && <CallHistoryView />}
          {activeTab === 'knowledge-base' && <KnowledgeBaseView />}
          {activeTab === 'settings' && (
            <SettingsView
              language={language}
              setLanguage={setLanguage}
            />
          )}
        </main>
      </div>
    </div>
  );
}
