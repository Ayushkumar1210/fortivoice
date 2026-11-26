import React, { useState, useEffect } from 'react';
import {
  PhoneCall,
  Clock,
  User,
  Calendar,
  FileText,
  Smile,
  Meh,
  Frown,
  Eye,
  Award,
  CheckCircle2,
  X
} from 'lucide-react';
import { api } from '../services/api';

export default function CallHistoryView() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCall, setSelectedCall] = useState(null);

  useEffect(() => {
    loadCalls();
  }, []);

  const loadCalls = async () => {
    try {
      setLoading(true);
      const data = await api.getCalls();
      setCalls(data);
    } catch (err) {
      console.error('Failed to load call history:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h3 className="text-xl font-bold text-white tracking-tight">Call History & AI Summaries</h3>
        <p className="text-xs text-slate-400">
          Autonomous audio call logs, conversational transcripts, and post-call executive summaries
        </p>
      </div>

      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/90 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3.5 px-6">Call ID & Customer</th>
                <th className="py-3.5 px-6">Call Date</th>
                <th className="py-3.5 px-6">Turns / Duration</th>
                <th className="py-3.5 px-6">Sentiment</th>
                <th className="py-3.5 px-6">Lead Qualification</th>
                <th className="py-3.5 px-6 text-right">Summary & Transcript</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-400">
                    Loading call transcripts...
                  </td>
                </tr>
              ) : calls.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-slate-400">
                    No calls recorded yet. Try starting a voice conversation in the AI Voice Agent tab!
                  </td>
                </tr>
              ) : (
                calls.map((call) => {
                  const id = call._id || call.id;
                  const isHot = call.lead_status === 'HOT';
                  const isWarm = call.lead_status === 'WARM';

                  return (
                    <tr
                      key={id}
                      onClick={() => setSelectedCall(call)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-4 px-6 font-semibold text-white">
                        <div>
                          <p>{call.customer_name || 'Inbound Prospect'}</p>
                          <p className="text-[11px] font-mono text-slate-500">{call.call_id}</p>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-slate-300">
                        {call.created_at ? new Date(call.created_at).toLocaleString() : 'Recent'}
                      </td>
                      <td className="py-4 px-6">
                        <span className="font-semibold text-slate-200">
                          {call.messages ? call.messages.length : 0} messages
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`text-xs font-semibold ${
                            call.sentiment === 'Positive'
                              ? 'text-emerald-400'
                              : call.sentiment === 'Negative'
                              ? 'text-rose-400'
                              : 'text-slate-400'
                          }`}
                        >
                          {call.sentiment || 'Neutral'}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        {call.lead_status ? (
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider border ${
                              isHot
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                : isWarm
                                ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                                : 'bg-slate-700/60 text-slate-300 border-slate-600'
                            }`}
                          >
                            {call.lead_status} ({call.lead_score || 50}/100)
                          </span>
                        ) : (
                          <span className="text-slate-500">Unscored</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCall(call);
                          }}
                          className="py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold inline-flex items-center gap-1.5 transition-all"
                        >
                          <Eye className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Review</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Call Details & Transcript Modal */}
      {selectedCall && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <PhoneCall className="w-5 h-5 text-emerald-400" />
                  <span>Call Details: {selectedCall.customer_name}</span>
                </h3>
                <p className="text-xs font-mono text-slate-400">{selectedCall.call_id}</p>
              </div>
              <button
                onClick={() => setSelectedCall(null)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* AI Summary Section */}
            {selectedCall.summary && (
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  Executive Call Summary
                </h4>
                <p className="text-xs text-slate-200 leading-relaxed">{selectedCall.summary}</p>
              </div>
            )}

            {/* Requirements & Next Steps */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">
                  Identified Requirements
                </span>
                <p className="text-slate-300">{selectedCall.requirements || 'General sales inquiry'}</p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">
                  Customer Objections
                </span>
                <p className="text-slate-300">{selectedCall.objections || 'None recorded'}</p>
              </div>
            </div>

            {selectedCall.next_action && (
              <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-xs">
                <span className="text-[10px] text-emerald-400 uppercase font-bold block mb-1">
                  Recommended Next Action
                </span>
                <p className="font-semibold text-white">{selectedCall.next_action}</p>
              </div>
            )}

            {/* Full Transcript */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Full Conversation Transcript
              </h4>
              <div className="space-y-2.5 max-h-[220px] overflow-y-auto p-3 rounded-xl bg-slate-950 border border-slate-800">
                {selectedCall.messages && selectedCall.messages.length > 0 ? (
                  selectedCall.messages.map((m, idx) => {
                    const isAgent = m.sender === 'agent';
                    return (
                      <div key={idx} className="text-xs">
                        <span
                          className={`font-bold mr-1.5 ${
                            isAgent ? 'text-emerald-400' : 'text-blue-400'
                          }`}
                        >
                          {isAgent ? 'FortiVoice AI:' : 'Customer:'}
                        </span>
                        <span className="text-slate-300">{m.text}</span>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-slate-500">No transcript messages saved.</p>
                )}
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedCall(null)}
                className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
