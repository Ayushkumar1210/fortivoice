import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  Filter,
  Plus,
  RefreshCw,
  Flame,
  Award,
  Phone,
  Mail,
  DollarSign,
  Calendar,
  Trash2,
  Eye,
  CheckCircle2,
  X
} from 'lucide-react';
import { api } from '../services/api';

export default function LeadsView() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Selected lead modal for detailed view
  const [selectedLead, setSelectedLead] = useState(null);
  
  // Add lead modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newLead, setNewLead] = useState({
    name: '',
    company: '',
    phone: '',
    email: '',
    product_interest: 'Professional Growth Plan',
    budget: '$1,500 / month',
    requirements: '',
    timeline: 'Immediate',
    status: 'WARM',
    score: 65,
    sentiment: 'Positive'
  });

  useEffect(() => {
    loadLeads();
  }, [statusFilter]);

  const loadLeads = async () => {
    try {
      setLoading(true);
      const data = await api.getLeads(statusFilter, searchQuery);
      setLeads(data);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadLeads();
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this lead?')) return;
    try {
      await api.deleteLead(id);
      setLeads((prev) => prev.filter((l) => (l._id || l.id) !== id));
      if (selectedLead && (selectedLead._id || selectedLead.id) === id) {
        setSelectedLead(null);
      }
    } catch (err) {
      console.error('Failed to delete lead:', err);
    }
  };

  const handleCreateLead = async (e) => {
    e.preventDefault();
    try {
      await api.createLead(newLead);
      setShowAddModal(false);
      setNewLead({
        name: '',
        phone: '',
        email: '',
        product_interest: 'Professional Growth Plan',
        budget: '$1,500 / month',
        requirements: '',
        timeline: 'Immediate',
        status: 'WARM',
        score: 65,
        sentiment: 'Positive'
      });
      loadLeads();
    } catch (err) {
      console.error('Failed to create lead:', err);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">Leads Management</h3>
          <p className="text-xs text-slate-400">
            Real-time qualification scores, requirements & contact intelligence
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Form */}
          <form onSubmit={handleSearch} className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search leads..."
              className="bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-48 lg:w-64"
            />
          </form>

          {/* Filter Pills */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
            {['', 'HOT', 'WARM', 'COLD'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  statusFilter === st
                    ? 'bg-slate-800 text-emerald-400 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st === '' ? 'All Tiers' : st}
              </button>
            ))}
          </div>

          {/* Refresh Leads */}
          <button
            onClick={loadLeads}
            className="py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs flex items-center gap-1.5 transition-all"
            title="Refresh Leads from Database"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {/* Add Lead */}
          <button
            onClick={() => setShowAddModal(true)}
            className="py-2 px-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Lead</span>
          </button>
        </div>
      </div>

      {/* Leads Table Card */}
      <div className="rounded-2xl craft-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] bg-[#0e1219]/90 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3.5 px-6">Prospect Name</th>
                <th className="py-3.5 px-6">Contact Info</th>
                <th className="py-3.5 px-6">Product & Budget</th>
                <th className="py-3.5 px-6">AI Score</th>
                <th className="py-3.5 px-6">Status</th>
                <th className="py-3.5 px-6">Sentiment</th>
                <th className="py-3.5 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-xs text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-400">
                    Loading CRM leads...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-400">
                    No leads found matching query.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => {
                  const id = lead._id || lead.id;
                  const isHot = lead.status === 'HOT';
                  const isWarm = lead.status === 'WARM';

                  return (
                    <tr
                      key={id}
                      onClick={() => setSelectedLead(lead)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-4 px-6 font-semibold text-white">
                        <div className="space-y-0.5">
                          <p className="font-semibold text-white">{lead.name || 'Anonymous Prospect'}</p>
                          {lead.company && (
                            <p className="text-[11px] font-medium text-emerald-400">
                              {lead.company}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="space-y-0.5">
                          <p className="text-slate-200">{lead.phone || 'No phone'}</p>
                          <p className="text-[11px] text-slate-400">{lead.email || 'No email'}</p>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="space-y-0.5">
                          <p className="font-medium text-slate-200">
                            {lead.product_interest || 'Enterprise Solution'}
                          </p>
                          <p className="text-[11px] text-emerald-400 font-semibold">
                            {lead.budget || 'Custom'}
                          </p>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{lead.score || 50}</span>
                          <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                isHot
                                  ? 'bg-amber-400'
                                  : isWarm
                                  ? 'bg-blue-400'
                                  : 'bg-slate-500'
                              }`}
                              style={{ width: `${lead.score || 50}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold tracking-wider uppercase border ${
                            isHot
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              : isWarm
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                              : 'bg-slate-700/60 text-slate-300 border-slate-600'
                          }`}
                        >
                          {lead.status}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span
                          className={`text-xs font-medium ${
                            lead.sentiment === 'Positive'
                              ? 'text-emerald-400'
                              : lead.sentiment === 'Negative'
                              ? 'text-rose-400'
                              : 'text-slate-400'
                          }`}
                        >
                          {lead.sentiment || 'Neutral'}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedLead(lead);
                            }}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => handleDelete(id, e)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-900/50 text-slate-400 hover:text-rose-400 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lead Detail Modal */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedLead.name}</h3>
                <p className="text-xs text-slate-400">Detailed Lead Intelligence</p>
              </div>
              <button
                onClick={() => setSelectedLead(null)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">
                    AI Lead Score
                  </span>
                  <span className="text-lg font-extrabold text-white">
                    {selectedLead.score}/100
                  </span>
                  <span className="text-[11px] text-amber-400 font-bold ml-2">
                    ({selectedLead.status})
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">
                    Customer Sentiment
                  </span>
                  <span className="text-lg font-extrabold text-white">
                    {selectedLead.sentiment || 'Neutral'}
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">
                  Scoring Rationale
                </span>
                <p className="text-slate-300 italic">
                  "{selectedLead.score_reasoning || 'Lead established initial communication with sales specialist.'}"
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                <span className="text-[10px] text-slate-500 uppercase font-bold block">
                  Product & Commercial Fit
                </span>
                <div className="grid grid-cols-2 gap-2 text-slate-300">
                  <div>Company: <strong className="text-emerald-400">{selectedLead.company || 'Not Specified'}</strong></div>
                  <div>Interest: <strong className="text-white">{selectedLead.product_interest || 'N/A'}</strong></div>
                  <div>Budget: <strong className="text-white">{selectedLead.budget || 'N/A'}</strong></div>
                  <div>Timeline: <strong className="text-white">{selectedLead.timeline || 'N/A'}</strong></div>
                  <div>Phone: <strong className="text-white">{selectedLead.phone || 'N/A'}</strong></div>
                  <div>Email: <strong className="text-white">{selectedLead.email || 'N/A'}</strong></div>
                </div>
              </div>

              {selectedLead.requirements && (
                <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">
                    Customer Requirements
                  </span>
                  <p className="text-slate-300">{selectedLead.requirements}</p>
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedLead(null)}
                className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Lead Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateLead}
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Create New Lead</h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-2">
                <label className="text-slate-400 block mb-1">Prospect Name</label>
                <input
                  type="text"
                  required
                  value={newLead.name}
                  onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
                  placeholder="e.g. Alex Mercer"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Company / Organization</label>
                <input
                  type="text"
                  value={newLead.company}
                  onChange={(e) => setNewLead({ ...newLead, company: e.target.value })}
                  placeholder="e.g. Acme Corp"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Phone</label>
                <input
                  type="text"
                  value={newLead.phone}
                  onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
                  placeholder="+1 (555) 000-0000"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Email</label>
                <input
                  type="email"
                  value={newLead.email}
                  onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
                  placeholder="alex@company.com"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Budget</label>
                <input
                  type="text"
                  value={newLead.budget}
                  onChange={(e) => setNewLead({ ...newLead, budget: e.target.value })}
                  placeholder="$2,000 / mo"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Qualification Tier</label>
                <select
                  value={newLead.status}
                  onChange={(e) => {
                    const st = e.target.value;
                    const sc = st === 'HOT' ? 85 : st === 'WARM' ? 60 : 30;
                    setNewLead({ ...newLead, status: st, score: sc });
                  }}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="HOT">HOT (85 pts)</option>
                  <option value="WARM">WARM (60 pts)</option>
                  <option value="COLD">COLD (30 pts)</option>
                </select>
              </div>

              <div className="col-span-2">
                <label className="text-slate-400 block mb-1">Requirements / Notes</label>
                <textarea
                  rows="2"
                  value={newLead.requirements}
                  onChange={(e) => setNewLead({ ...newLead, requirements: e.target.value })}
                  placeholder="Specific use case or pain points..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                ></textarea>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="py-2 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-bold text-xs"
              >
                Save Lead
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
