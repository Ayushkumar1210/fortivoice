import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  PhoneOff,
  Sparkles,
  Award,
  Calendar,
  Send,
  User,
  Phone,
  Mail,
  DollarSign,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  Smile,
  Meh,
  Frown,
  BookOpen
} from 'lucide-react';
import AudioWaveform from './AudioWaveform';
import { speechService } from '../services/speechService';
import { api } from '../services/api';

export default function VoiceAgentView({ language, setLanguage, onSummaryCreated, systemStatus }) {
  const [sessionId, setSessionId] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [agentStatus, setAgentStatus] = useState('idle'); // 'idle' | 'listening' | 'thinking' | 'speaking'
  const [transcript, setTranscript] = useState([]);
  const [interimText, setInterimText] = useState('');
  const [manualInput, setManualInput] = useState('');
  
  // Real-time extracted lead profile & score
  const [leadProfile, setLeadProfile] = useState({
    name: '',
    company: '',
    phone: '',
    email: '',
    product_interest: '',
    budget: '',
    timeline: '',
    requirements: ''
  });
  const [leadScore, setLeadScore] = useState(50);
  const [leadStatus, setLeadStatus] = useState('WARM');
  const [scoreReasoning, setScoreReasoning] = useState('Session initialized. Awaiting customer dialogue.');
  const [sentiment, setSentiment] = useState('Neutral');
  const [sentimentScore, setSentimentScore] = useState(0.0);
  const [bookedAppointment, setBookedAppointment] = useState(null);
  const [ragSources, setRagSources] = useState([]);
  const [activeEngineMode, setActiveEngineMode] = useState(systemStatus?.active_engine || (systemStatus?.gemini?.mode === 'live' ? 'live_gemini' : 'local_demo'));

  useEffect(() => {
    if (systemStatus?.active_engine) {
      setActiveEngineMode(systemStatus.active_engine);
    }
  }, [systemStatus]);

  // Post-call Summary Modal state
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [summaryData, setSummaryData] = useState(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState('');

  const transcriptEndRef = useRef(null);
  const micSessionActiveRef = useRef(false);
  const cooldownTimerRef = useRef(null);

  // Initialize new session & cleanup voice on unmount
  useEffect(() => {
    resetCallSession();
    return () => {
      if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
      micSessionActiveRef.current = false;
      speechService.cancelSpeech();
      speechService.stopListening();
      setIsListening(false);
      setIsSpeaking(false);
      setAgentStatus('idle');
    };
  }, []);

  // Update speech service language when language prop changes
  useEffect(() => {
    speechService.setLanguage(language);
  }, [language]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, interimText]);

  const resetCallSession = () => {
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    micSessionActiveRef.current = false;
    speechService.cancelSpeech();
    speechService.stopListening();
    setIsListening(false);
    setIsSpeaking(false);
    setAgentStatus('idle');

    const newId = `call-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setSessionId(newId);

    // Initial greeting message
    const initialGreeting =
      language === 'hi'
        ? 'Namaste! Main FortiVoice hoon, aapka autonomous AI sales specialist. FortiCloud ke enterprise solutions ke baare mein aap kya janna chahte hain?'
        : 'Hello! I am FortiVoice, your autonomous AI sales specialist. We empower enterprises with intelligent voice automation and CRM synchronization. How can I help your business today?';

    setTranscript([
      {
        sender: 'agent',
        text: initialGreeting,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);

    setLeadProfile({
      name: '',
      company: '',
      phone: '',
      email: '',
      product_interest: '',
      budget: '',
      timeline: '',
      requirements: ''
    });
    setLeadScore(50);
    setLeadStatus('WARM');
    setScoreReasoning('Awaiting initial customer input.');
    setSentiment('Neutral');
    setBookedAppointment(null);
    setRagSources([]);

    // Speak initial greeting if user clicked
    setTimeout(() => {
      speechService.speak(initialGreeting, {
        onStart: () => {
          setIsSpeaking(true);
          setAgentStatus('speaking');
        },
        onEnd: () => {
          setIsSpeaking(false);
          setAgentStatus('idle');
        }
      });
    }, 400);
  };

  // Start microphone listening session with acoustic echo guard
  const startListeningSession = () => {
    speechService.cancelSpeech();
    setIsSpeaking(false);

    return speechService.startListening({
      onStart: () => {
        setIsListening(true);
        micSessionActiveRef.current = true;
        setAgentStatus('listening');
      },
      onResult: ({ final, interim }) => {
        if (interim) {
          setInterimText(interim);
        }
        if (final) {
          setInterimText('');
          handleUserMessage(final);
        }
      },
      onError: (err) => {
        console.warn('Speech recognition error:', err);
        setIsListening(false);
        setAgentStatus('idle');
      },
      onEnd: () => {
        setIsListening(false);
        if (!speechService.isSpeaking) {
          setAgentStatus('idle');
        }
      }
    });
  };

  // Toggle Microphone
  const toggleListening = () => {
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }

    if (isListening || micSessionActiveRef.current) {
      micSessionActiveRef.current = false;
      speechService.stopListening();
      setIsListening(false);
      setAgentStatus('idle');
      setInterimText('');
    } else {
      const success = startListeningSession();
      if (!success) {
        alert('Could not start microphone. You can also type in the message box below.');
      }
    }
  };

  // Send Customer Message to Backend
  const handleUserMessage = async (text) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    // Guard against acoustic self-echo
    if (speechService.isSelfEcho(cleanText)) {
      console.warn('Blocked self-voice echo loop in UI:', cleanText);
      return;
    }

    // Immediately stop listening while AI is thinking and speaking
    speechService.stopListening();
    setIsListening(false);

    // Append to transcript
    const userMsg = {
      sender: 'customer',
      text: cleanText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setTranscript((prev) => [...prev, userMsg]);
    setAgentStatus('thinking');

    try {
      const response = await api.interactVoice({
        session_id: sessionId,
        message: cleanText,
        language: language,
        customer_profile: leadProfile,
        conversation_history: transcript.map((m) => ({
          sender: m.sender,
          text: m.text
        }))
      });

      // Update lead attributes safely without overwriting with nulls
      if (response.extracted_lead) {
        setLeadProfile((prev) => {
          const updated = { ...prev };
          Object.entries(response.extracted_lead).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '') {
              updated[k] = v;
            }
          });
          return updated;
        });
      }

      if (response.engine_mode) setActiveEngineMode(response.engine_mode);
      if (response.lead_score !== undefined) setLeadScore(response.lead_score);
      if (response.lead_status) setLeadStatus(response.lead_status);
      if (response.score_reasoning) setScoreReasoning(response.score_reasoning);
      if (response.sentiment) setSentiment(response.sentiment);
      if (response.sentiment_score !== undefined) setSentimentScore(response.sentiment_score);
      if (response.rag_sources) setRagSources(response.rag_sources);

      // Check appointment booking
      if (response.appointment_intent && response.appointment_intent.requested) {
        setBookedAppointment({
          date: response.appointment_intent.preferred_date,
          time: response.appointment_intent.preferred_time || '14:00',
          purpose: response.appointment_intent.purpose || 'FortiVoice VIP Consultation'
        });
      }

      // Append agent reply to transcript
      const agentMsg = {
        sender: 'agent',
        text: response.reply_text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTranscript((prev) => [...prev, agentMsg]);
      setAgentStatus('idle');

      // Speak agent reply via TTS
      speechService.speak(response.speech_text || response.reply_text, {
        onStart: () => {
          setIsSpeaking(true);
          setAgentStatus('speaking');
          speechService.stopListening();
          setIsListening(false);
        },
        onEnd: () => {
          setIsSpeaking(false);
          setAgentStatus('idle');

          // Acoustic Echo Defense: Add 550ms safety cooldown for speaker reverb to fade before re-engaging mic
          if (micSessionActiveRef.current) {
            if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
            cooldownTimerRef.current = setTimeout(() => {
              if (micSessionActiveRef.current) {
                startListeningSession();
              }
            }, 550);
          }
        },
        onError: () => {
          setIsSpeaking(false);
          setAgentStatus('idle');
        }
      });
    } catch (err) {
      console.error('Error in voice interaction:', err);
      setAgentStatus('idle');
      const errorMsg = {
        sender: 'agent',
        text: "I apologize, I experienced a brief connection glitch. Could you please repeat that?",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTranscript((prev) => [...prev, errorMsg]);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualInput.trim()) return;
    const text = manualInput;
    setManualInput('');
    handleUserMessage(text);
  };

  // End Call & Trigger AI Summary
  const handleEndCall = async () => {
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }
    micSessionActiveRef.current = false;
    speechService.cancelSpeech();
    speechService.stopListening();
    setIsListening(false);
    setIsSpeaking(false);
    setIsSummarizing(true);
    setSummaryError('');
    setShowSummaryModal(true);

    try {
      const summary = await api.generateCallSummary({
        session_id: sessionId,
        messages: transcript.map((m) => ({
          sender: m.sender,
          text: m.text,
          timestamp: m.timestamp || new Date().toISOString()
        })),
        customer_profile: leadProfile
      });
      setSummaryData(summary);
      if (onSummaryCreated) onSummaryCreated();
    } catch (err) {
      console.error('Failed to generate call summary:', err);
      setSummaryError(err.message || 'Could not retrieve summary. Please verify your connection and try again.');
    } finally {
      setIsSummarizing(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto h-[calc(100vh-4rem)] flex flex-col gap-6">
      {/* Top Console Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl craft-card">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                agentStatus === 'speaking'
                  ? 'bg-emerald-400 animate-ping'
                  : agentStatus === 'listening'
                  ? 'bg-blue-400 animate-pulse'
                  : agentStatus === 'thinking'
                  ? 'bg-amber-400 animate-spin'
                  : 'bg-slate-500'
              }`}
            ></span>
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              {agentStatus === 'speaking'
                ? 'FortiVoice Speaking'
                : agentStatus === 'listening'
                ? 'Customer Speaking...'
                : agentStatus === 'thinking'
                ? (activeEngineMode === 'live_groq'
                    ? 'Groq AI Reasoning & RAG Retrieval...'
                    : activeEngineMode === 'live_gemini'
                    ? 'Gemini AI Reasoning & RAG Retrieval...'
                    : 'AI Reasoning & RAG Retrieval...')
                : 'Agent Ready'}
            </span>
          </div>
          <span className="text-slate-600">•</span>
          <span className="text-xs font-mono text-slate-400">ID: {sessionId.slice(0, 15)}</span>
          <span className="text-slate-600">•</span>
          {activeEngineMode === 'live_gemini' && (
            <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              ✨ LIVE GEMINI AI
            </span>
          )}
          {activeEngineMode === 'live_groq' && (
            <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30">
              ⚡ LIVE GROQ AI
            </span>
          )}
          {activeEngineMode !== 'live_gemini' && activeEngineMode !== 'live_groq' && (
            <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              ⚡ LOCAL DEMO ENGINE
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Mute Speaking */}
          {isSpeaking && (
            <button
              onClick={() => speechService.cancelSpeech()}
              className="py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <VolumeX className="w-3.5 h-3.5 text-rose-400" />
              <span>Interrupt Voice</span>
            </button>
          )}

          {/* End Call & Summarize */}
          <button
            onClick={handleEndCall}
            className="py-1.5 px-4 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
          >
            <PhoneOff className="w-3.5 h-3.5" />
            <span>End Call & Summarize</span>
          </button>

          {/* Reset Call */}
          <button
            onClick={resetCallSession}
            className="py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all"
          >
            New Call
          </button>
        </div>
      </div>

      {/* Main Split Interface */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left: Voice Interaction Console & Transcript (7 cols) */}
        <div className="lg:col-span-7 flex flex-col rounded-2xl craft-card overflow-hidden">
          {/* Waveform & Mic Section */}
          <div className="p-6 border-b border-white/[0.06] bg-gradient-to-b from-black/50 via-[#0e1219]/90 to-[#0b0e14] flex flex-col items-center justify-center gap-4 relative">
            <AudioWaveform isListening={isListening} isSpeaking={isSpeaking} />

            {/* Central Mic Button */}
            <div className="relative">
              {isListening && (
                <div className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping"></div>
              )}
              {isSpeaking && (
                <div className="absolute inset-0 rounded-full bg-emerald-500/20 animate-ping"></div>
              )}
              <button
                onClick={toggleListening}
                className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 active:scale-95 ${
                  isListening
                    ? 'bg-gradient-to-tr from-blue-600 to-cyan-500 text-white studio-mic-listening-glow ring-4 ring-blue-500/30'
                    : isSpeaking
                    ? 'bg-gradient-to-tr from-emerald-600 to-teal-400 text-white studio-mic-glow ring-4 ring-emerald-500/30'
                    : 'bg-[#151a24] hover:bg-[#1a212e] text-emerald-400 border border-white/10 shadow-[0_8px_24px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.1)]'
                }`}
              >
                {isListening ? (
                  <Mic className="w-8 h-8 animate-pulse text-white" />
                ) : (
                  <Mic className="w-8 h-8 text-emerald-400" />
                )}
              </button>
            </div>

            <p className="text-xs font-semibold text-slate-400 text-center">
              {isListening
                ? 'Listening... Click to stop or pause speaking'
                : isSpeaking
                ? 'Speaking AI response...'
                : 'Click microphone to speak with FortiVoice'}
            </p>
          </div>

          {/* Transcript Scroll Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {transcript.map((msg, idx) => {
              const isAgent = msg.sender === 'agent';
              return (
                <div
                  key={idx}
                  className={`flex flex-col ${isAgent ? 'items-start' : 'items-end'}`}
                >
                  <div className="flex items-center gap-2 mb-1 text-[11px] text-slate-400">
                    <span className="font-semibold text-slate-300">
                      {isAgent ? 'FortiVoice AI' : 'Prospect'}
                    </span>
                    <span>•</span>
                    <span>{msg.timestamp}</span>
                  </div>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                      isAgent
                        ? 'bg-slate-800/90 text-slate-100 border border-slate-700/60 rounded-tl-sm'
                        : 'bg-emerald-600 text-white rounded-tr-sm font-medium'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              );
            })}

            {/* Interim live speech recognition bubble */}
            {interimText && (
              <div className="flex flex-col items-end">
                <span className="text-[11px] text-blue-400 mb-1">Transcribing...</span>
                <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm bg-blue-600/40 border border-blue-500/50 text-blue-100 rounded-tr-sm italic animate-pulse">
                  {interimText}
                </div>
              </div>
            )}

            <div ref={transcriptEndRef} />
          </div>

          {/* Bottom Manual Text Input Fallback */}
          <form
            onSubmit={handleManualSubmit}
            className="p-3.5 border-t border-white/[0.06] bg-black/35 flex items-center gap-2"
          >
            <input
              type="text"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Or type your inquiry here (e.g., 'What is your pricing?' or 'Book a demo tomorrow at 2 PM')..."
              className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/20 transition-all"
            />
            <button
              type="submit"
              className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white shadow-md shadow-emerald-500/25 active:scale-95 transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Right: Live AI Lead Qualification & CRM Sync Panel (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-5 overflow-y-auto pr-1">
          {/* Lead Qualification & Score Card */}
          <div className="p-6 rounded-2xl craft-card space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-base font-bold text-white tracking-tight">
                  Intelligent Lead Qualification
                </h4>
                <div className="flex items-center gap-2 mt-0.5">
                  <p className="text-xs text-slate-400">Live AI scoring & classification</p>
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1">
                    ✓ Synced to CRM (MongoDB)
                  </span>
                </div>
              </div>

              {/* Status Badge */}
              <div
                className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wider border shadow-sm ${
                  leadStatus === 'HOT'
                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                    : leadStatus === 'WARM'
                    ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                    : 'bg-slate-700 text-slate-300 border-slate-600'
                }`}
              >
                {leadStatus} LEAD
              </div>
            </div>

            {/* Score Meter */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-2">
                <span className="text-slate-300">Lead Readiness Score</span>
                <span className="text-xl font-extrabold text-white">{leadScore} / 100</span>
              </div>
              <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    leadScore >= 75
                      ? 'bg-gradient-to-r from-amber-500 to-red-500'
                      : leadScore >= 40
                      ? 'bg-gradient-to-r from-blue-500 to-emerald-400'
                      : 'bg-slate-600'
                  }`}
                  style={{ width: `${leadScore}%` }}
                ></div>
              </div>
              <p className="text-xs text-slate-400 mt-2 italic font-medium">
                "{scoreReasoning}"
              </p>
            </div>

            {/* Extracted Customer Attributes */}
            <div className="space-y-2.5 pt-2 border-t border-slate-800/80">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                Extracted Attributes
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] hover:bg-white/[0.06] transition-all flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500 uppercase">Name</p>
                    <p className="font-semibold text-white truncate">
                      {leadProfile.name || 'Detecting...'}
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] hover:bg-white/[0.06] transition-all flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500 uppercase">Company</p>
                    <p className="font-semibold text-white truncate">
                      {leadProfile.company || 'Detecting...'}
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] hover:bg-white/[0.06] transition-all flex items-center gap-2">
                  <Phone className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500 uppercase">Phone</p>
                    <p className="font-semibold text-white truncate">
                      {leadProfile.phone || 'Awaiting phone'}
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] hover:bg-white/[0.06] transition-all flex items-center gap-2">
                  <Mail className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500 uppercase">Email</p>
                    <p className="font-semibold text-white truncate">
                      {leadProfile.email || 'Awaiting email'}
                    </p>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] hover:bg-white/[0.06] transition-all flex items-center gap-2 col-span-2">
                  <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-slate-500 uppercase">Budget</p>
                    <p className="font-semibold text-white truncate">
                      {leadProfile.budget || 'Not stated'}
                    </p>
                  </div>
                </div>
              </div>

              {leadProfile.product_interest && (
                <div className="p-2.5 rounded-xl bg-white/[0.035] border border-white/[0.06] text-xs">
                  <span className="text-[10px] text-slate-500 uppercase block">Product Interest</span>
                  <span className="font-semibold text-white">{leadProfile.product_interest}</span>
                </div>
              )}
            </div>

            {/* Sentiment Indicator */}
            <div className="p-3 rounded-xl bg-white/[0.035] border border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                {sentiment === 'Positive' ? (
                  <Smile className="w-5 h-5 text-emerald-400" />
                ) : sentiment === 'Negative' ? (
                  <Frown className="w-5 h-5 text-rose-400" />
                ) : (
                  <Meh className="w-5 h-5 text-blue-400" />
                )}
                <div>
                  <p className="text-xs font-bold text-white">Sentiment: {sentiment}</p>
                  <p className="text-[11px] text-slate-400">Tone index: {sentimentScore > 0 ? `+${sentimentScore}` : sentimentScore}</p>
                </div>
              </div>
              <span className="text-[11px] font-semibold text-slate-400">Live Voice NLP</span>
            </div>
          </div>

          {/* Appointment Notification Card */}
          {bookedAppointment && (
            <div className="p-5 rounded-2xl craft-card border-emerald-500/35 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <Calendar className="w-4 h-4" />
                <span>Appointment Booked Automatically</span>
              </div>
              <h5 className="text-base font-extrabold text-white">
                {bookedAppointment.purpose}
              </h5>
              <div className="text-xs text-slate-300 space-y-1">
                <p>📅 <strong>Date:</strong> {bookedAppointment.date}</p>
                <p>⏰ <strong>Time:</strong> {bookedAppointment.time}</p>
                <p className="text-emerald-400 font-medium">✓ Synced to MongoDB Appointments</p>
              </div>
            </div>
          )}

          {/* RAG Context Attribution Card */}
          {ragSources.length > 0 && (
            <div className="p-4 rounded-2xl craft-card space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <BookOpen className="w-4 h-4 text-emerald-400" />
                <span>RAG Grounding Sources</span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-300">
                {ragSources.slice(0, 2).map((s, idx) => (
                  <div key={idx} className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                    <p className="font-semibold text-emerald-400 text-[11px]">
                      {s.metadata?.source || 'FortiVoice Knowledge Base'}
                    </p>
                    <p className="line-clamp-2 text-slate-400 text-[11px] mt-0.5">{s.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Post-Call Summary Modal */}
      {showSummaryModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-emerald-400" />
                  <span>AI Executive Call Summary</span>
                </h3>
                <p className="text-xs text-slate-400">Autonomous post-call CRM briefing</p>
              </div>
              <button
                onClick={() => setShowSummaryModal(false)}
                className="text-slate-400 hover:text-white text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800"
              >
                Close
              </button>
            </div>

            {isSummarizing ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3">
                <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-sm font-semibold text-slate-300">
                  Synthesizing conversation, objection analysis & next actions...
                </p>
              </div>
            ) : summaryData ? (
              <div className="space-y-5 text-sm">
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
                    Call Overview
                  </h4>
                  <p className="text-slate-200 leading-relaxed bg-slate-800/40 p-3.5 rounded-xl border border-slate-800">
                    {summaryData.summary}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <h5 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1">
                      Customer Requirements
                    </h5>
                    <p className="text-xs text-slate-300">{summaryData.customer_requirements || summaryData.requirements || 'Standard enterprise inquiry'}</p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800">
                    <h5 className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-1">
                      Customer Objections
                    </h5>
                    <p className="text-xs text-slate-300">{summaryData.customer_objections || summaryData.objections || 'None noted'}</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 to-slate-800/50 border border-emerald-500/30 space-y-1">
                  <h5 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    Recommended Next Action
                  </h5>
                  <p className="text-xs font-semibold text-white">
                    {summaryData.recommended_next_action || summaryData.next_action || 'Follow up with customer proposal.'}
                  </p>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800">
                  <span>Lead Fit: <strong className="text-white">{summaryData.lead_status} ({summaryData.lead_score}/100)</strong></span>
                  <span>Recorded in MongoDB</span>
                </div>
              </div>
            ) : (
              <div className="py-6 space-y-3 text-center">
                <p className="text-xs text-rose-400 font-medium">
                  {summaryError || 'Could not retrieve summary.'}
                </p>
                <button
                  onClick={handleEndCall}
                  className="px-4 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold transition-all"
                >
                  Retry Summary Generation
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
