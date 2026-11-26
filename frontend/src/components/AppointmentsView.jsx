import React, { useState, useEffect } from 'react';
import {
  Calendar as CalendarIcon,
  Clock,
  User,
  Phone,
  Mail,
  Plus,
  CheckCircle2,
  XCircle,
  Trash2,
  Check,
  AlertCircle,
  X
} from 'lucide-react';
import { api } from '../services/api';

export default function AppointmentsView() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  // New appointment form state
  const [newApp, setNewApp] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    appointment_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    appointment_time: '14:00',
    purpose: 'FortiVoice VIP Product Demo & Architecture Review',
    notes: 'Booked via CRM console'
  });

  useEffect(() => {
    loadAppointments();
  }, [statusFilter]);

  const loadAppointments = async () => {
    try {
      setLoading(true);
      const data = await api.getAppointments(statusFilter);
      setAppointments(data);
    } catch (err) {
      console.error('Failed to load appointments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (id, newStatus) => {
    try {
      await api.updateAppointment(id, { status: newStatus });
      setAppointments((prev) =>
        prev.map((a) => ((a._id || a.id) === id ? { ...a, status: newStatus } : a))
      );
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Cancel and delete this appointment?')) return;
    try {
      await api.deleteAppointment(id);
      setAppointments((prev) => prev.filter((a) => (a._id || a.id) !== id));
    } catch (err) {
      console.error('Failed to delete appointment:', err);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.createAppointment(newApp);
      setShowAddModal(false);
      setNewApp({
        customer_name: '',
        customer_phone: '',
        customer_email: '',
        appointment_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
        appointment_time: '14:00',
        purpose: 'FortiVoice VIP Product Demo & Architecture Review',
        notes: 'Booked via CRM console'
      });
      loadAppointments();
    } catch (err) {
      alert(err.message || 'Failed to book appointment');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">
            Appointments & Demo Bookings
          </h3>
          <p className="text-xs text-slate-400">
            Validated calendar meetings booked autonomously by Voice AI and Sales Reps
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
            {['', 'Scheduled', 'Completed', 'Cancelled'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  statusFilter === st
                    ? 'bg-slate-800 text-emerald-400 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st === '' ? 'All Status' : st}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="py-2 px-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Book Appointment</span>
          </button>
        </div>
      </div>

      {/* Appointment Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {loading ? (
          <div className="col-span-3 py-12 text-center text-slate-400">
            Loading scheduled appointments...
          </div>
        ) : appointments.length === 0 ? (
          <div className="col-span-3 py-12 text-center text-slate-400">
            No appointments found.
          </div>
        ) : (
          appointments.map((app) => {
            const id = app._id || app.id;
            const isScheduled = app.status === 'Scheduled';
            const isCompleted = app.status === 'Completed';

            return (
              <div
                key={id}
                className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between space-y-4 hover:border-slate-700/80 transition-all shadow-lg"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider border ${
                        isScheduled
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : isCompleted
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                      }`}
                    >
                      {app.status}
                    </span>

                    <button
                      onClick={() => handleDelete(id)}
                      className="p-1 rounded-lg text-slate-500 hover:text-rose-400 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div>
                    <h4 className="text-base font-bold text-white tracking-tight">
                      {app.customer_name}
                    </h4>
                    <p className="text-xs text-emerald-400 font-medium mt-0.5">
                      {app.purpose || 'FortiVoice VIP Consultation'}
                    </p>
                  </div>

                  {/* Date & Time Pill */}
                  <div className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-800/50 border border-slate-800 text-xs text-slate-200">
                    <div className="flex items-center gap-1.5">
                      <CalendarIcon className="w-4 h-4 text-emerald-400" />
                      <span>{app.appointment_date}</span>
                    </div>
                    <span className="text-slate-600">•</span>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-emerald-400" />
                      <span>{app.appointment_time}</span>
                    </div>
                  </div>

                  <div className="space-y-1 text-xs text-slate-400">
                    {app.customer_phone && <p>📞 {app.customer_phone}</p>}
                    {app.customer_email && <p>✉️ {app.customer_email}</p>}
                    {app.notes && (
                      <p className="text-[11px] text-slate-400 italic pt-1 border-t border-slate-800">
                        "{app.notes}"
                      </p>
                    )}
                  </div>
                </div>

                {/* Quick Status Action */}
                {isScheduled && (
                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                    <button
                      onClick={() => handleStatusChange(id, 'Completed')}
                      className="flex-1 py-1.5 rounded-xl bg-slate-800 hover:bg-emerald-500/20 text-slate-300 hover:text-emerald-400 text-xs font-semibold flex items-center justify-center gap-1 transition-all"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Mark Done</span>
                    </button>
                    <button
                      onClick={() => handleStatusChange(id, 'Cancelled')}
                      className="py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-xs font-semibold transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Book Appointment Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreate}
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Schedule New Appointment</h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Customer / Prospect Name</label>
                <input
                  type="text"
                  required
                  value={newApp.customer_name}
                  onChange={(e) => setNewApp({ ...newApp, customer_name: e.target.value })}
                  placeholder="e.g. Jordan Hayes"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Appointment Date</label>
                  <input
                    type="date"
                    required
                    value={newApp.appointment_date}
                    onChange={(e) => setNewApp({ ...newApp, appointment_date: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Appointment Time</label>
                  <input
                    type="time"
                    required
                    value={newApp.appointment_time}
                    onChange={(e) => setNewApp({ ...newApp, appointment_time: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Customer Phone</label>
                  <input
                    type="text"
                    value={newApp.customer_phone}
                    onChange={(e) => setNewApp({ ...newApp, customer_phone: e.target.value })}
                    placeholder="+1 (555) 123-4567"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Customer Email</label>
                  <input
                    type="email"
                    value={newApp.customer_email}
                    onChange={(e) => setNewApp({ ...newApp, customer_email: e.target.value })}
                    placeholder="jordan@company.com"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Meeting Purpose</label>
                <input
                  type="text"
                  value={newApp.purpose}
                  onChange={(e) => setNewApp({ ...newApp, purpose: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                />
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
                Confirm Booking
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
