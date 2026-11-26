import React, { useState, useEffect } from 'react';
import {
  Database,
  UploadCloud,
  FileText,
  Search,
  CheckCircle2,
  Trash2,
  Sparkles,
  BookOpen,
  ArrowRight,
  Layers
} from 'lucide-react';
import { api } from '../services/api';

export default function KnowledgeBaseView() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  // RAG Query Tester
  const [testQuery, setTestQuery] = useState('');
  const [queryResults, setQueryResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setUploading(true);
      setUploadMsg(`Ingesting & chunking "${file.name}" into ChromaDB...`);
      await api.uploadDocument(file);
      setUploadMsg(`Successfully embedded ${file.name}!`);
      loadDocuments();
      setTimeout(() => setUploadMsg(''), 4000);
    } catch (err) {
      alert(err.message || 'Failed to upload document');
      setUploadMsg('');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this document from vector knowledge base?')) return;
    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => (d._id || d.id) !== id));
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleRunTestQuery = async (e) => {
    e.preventDefault();
    if (!testQuery.trim()) return;

    try {
      setSearching(true);
      const res = await api.queryRAG(testQuery, 4);
      setQueryResults(res.results || []);
    } catch (err) {
      console.error('RAG search test failed:', err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h3 className="text-xl font-bold text-white tracking-tight">
          RAG Knowledge Base & Document Ingestion
        </h3>
        <p className="text-xs text-slate-400">
          Upload PDF & TXT documents to ground FortiVoice AI answers strictly in corporate knowledge
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Document Management & Uploader (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {/* File Upload Box */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border-2 border-dashed border-slate-700/80 hover:border-emerald-500/50 transition-all text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
              <UploadCloud className="w-6 h-6" />
            </div>

            <div>
              <h4 className="text-sm font-bold text-white">Upload Company Documents</h4>
              <p className="text-xs text-slate-400 mt-1">
                Supports PDF (.pdf) or Plain Text (.txt) files
              </p>
            </div>

            <label className="inline-block py-2 px-5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-xs cursor-pointer shadow-md shadow-emerald-500/20 active:scale-95 transition-all">
              <span>{uploading ? 'Processing Embeddings...' : 'Browse Document'}</span>
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>

            {uploadMsg && (
              <p className="text-xs font-semibold text-emerald-400 animate-pulse">{uploadMsg}</p>
            )}
          </div>

          {/* Ingested Documents List */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                <span>Ingested Vector Knowledge</span>
              </h4>
              <span className="text-xs font-semibold text-slate-400">
                {documents.length + 1} Documents Active
              </span>
            </div>

            {/* Default pre-seeded document */}
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-white">
                    fortivoice_enterprise_playbook.txt
                  </p>
                  <p className="text-[11px] text-slate-400">
                    System Default • Pricing, SLAs, Tiers & Policies
                  </p>
                </div>
              </div>
              <span className="text-[10px] font-bold text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                Permanent Core
              </span>
            </div>

            {/* Uploaded Documents */}
            <div className="space-y-2">
              {documents.map((doc) => {
                const id = doc._id || doc.id;
                return (
                  <div
                    key={id}
                    className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-blue-400 shrink-0" />
                      <div>
                        <p className="text-xs font-bold text-white">{doc.filename}</p>
                        <p className="text-[11px] text-slate-400">
                          {doc.chunk_count} chunks • {doc.file_size_kb} KB •{' '}
                          {doc.file_type?.toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Interactive RAG Vector Retrieval Test Bench (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 space-y-4">
            <div>
              <h4 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>RAG Retrieval Test Bench</span>
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                Test semantic search queries against ChromaDB to verify context grounding
              </p>
            </div>

            {/* Query Form */}
            <form onSubmit={handleRunTestQuery} className="flex gap-2">
              <input
                type="text"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                placeholder="e.g. 'What is the pricing for Starter plan?' or 'Is there an SLA?'"
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={searching}
                className="py-2.5 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
              >
                <span>{searching ? 'Querying...' : 'Search'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>

            {/* Quick Sample Queries */}
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              <span className="text-slate-500 py-1 font-semibold">Try:</span>
              {[
                'How much does Starter cost?',
                'Enterprise SLA & response time',
                'Do you support Hindi?',
                'What is the refund policy?'
              ].map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setTestQuery(q)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Results Display */}
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Retrieved Context Chunks ({queryResults.length})
              </div>

              {queryResults.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center">
                  Execute a search above to inspect semantic matching and similarity scores.
                </p>
              ) : (
                queryResults.map((res, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-800 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-bold text-emerald-400">
                        {res.metadata?.source || 'Company Knowledge'}
                      </span>
                      <span className="text-slate-400 font-mono">
                        Similarity: {res.score ? Math.round(res.score * 100) : 90}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed">{res.text}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
