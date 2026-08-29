import { useState, useEffect } from 'react';
import api from '../services/api';
import { Shield, Plus, Trash2, ShieldAlert } from 'lucide-react';

export default function WatchlistManagement() {
  const [watchlist, setWatchlist] = useState([]);
  const [plate, setPlate] = useState('');
  const [category, setCategory] = useState('WANTED VEHICLE');
  const [priority, setPriority] = useState('HIGH');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const res = await api.get('/watchlist');
      setWatchlist(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!plate) return;
    setLoading(true);
    try {
      await api.post('/watchlist', {
        registration_number: plate,
        category,
        priority,
        description
      });
      setPlate('');
      setDescription('');
      fetchWatchlist();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id) => {
    if (!window.confirm("Remove this vehicle from the watchlist?")) return;
    try {
      await api.delete(`/watchlist/${id}`);
      fetchWatchlist();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-4 md:p-8 text-white max-w-7xl mx-auto min-h-screen bg-transparent">
      <div className="flex items-center gap-4 mb-8 bg-slate-800/80 backdrop-blur-xl p-6 rounded-3xl border border-slate-700/50 shadow-2xl">
        <div className="bg-red-500/20 p-4 rounded-2xl border border-red-500/30">
          <ShieldAlert className="text-red-500 w-8 h-8" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Active Watchlist</h1>
          <p className="text-slate-400">Live AI matching automatically alerts on these registrations.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* ADD TO WATCHLIST FORM */}
        <div className="bg-slate-800/80 p-6 rounded-3xl border border-slate-700/50 shadow-xl h-fit">
          <h2 className="text-xl font-bold mb-6 flex items-center"><Plus className="w-5 h-5 mr-2 text-blue-400" /> Add New Target</h2>
          <form onSubmit={handleAdd} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-1">REGISTRATION NUMBER <span className="text-red-500">*</span></label>
              <input type="text" value={plate} onChange={(e) => setPlate(e.target.value.toUpperCase())} required placeholder="GJ01AB1234" className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-white focus:border-blue-500 font-mono uppercase" />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-1">CATEGORY</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-white focus:border-blue-500">
                <option value="WANTED VEHICLE">Wanted Vehicle</option>
                <option value="STOLEN VEHICLE">Stolen Vehicle</option>
                <option value="BLACKLISTED VEHICLE">Blacklisted Vehicle</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-1">PRIORITY</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-white focus:border-blue-500">
                <option value="HIGH">CRITICAL / HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-1">CASE DESCRIPTION</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-white focus:border-blue-500 h-24" placeholder="Case details or reasons..."></textarea>
            </div>
            <button type="submit" disabled={loading} className="w-full bg-red-600 hover:bg-red-500 text-white font-bold p-4 rounded-xl transition-all shadow-[0_0_15px_rgba(220,38,38,0.3)]">
              {loading ? "Adding..." : "Add to Watchlist"}
            </button>
          </form>
        </div>

        {/* WATCHLIST TABLE */}
        <div className="lg:col-span-2 bg-slate-800/80 p-6 rounded-3xl border border-slate-700/50 shadow-xl overflow-hidden">
          <h2 className="text-xl font-bold mb-6 flex items-center"><Shield className="w-5 h-5 mr-2 text-indigo-400" /> Database targets</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400 text-xs">
                  <th className="pb-3 px-4">VEHICLE NO</th>
                  <th className="pb-3 px-4">CATEGORY</th>
                  <th className="pb-3 px-4">PRIORITY</th>
                  <th className="pb-3 px-4">STATUS</th>
                  <th className="pb-3 px-4">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map(item => (
                  <tr key={item.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-4 px-4 font-mono font-bold text-red-400 tracking-wider text-base">{item.registration_number}</td>
                    <td className="py-4 px-4 text-sm font-semibold">{item.category}</td>
                    <td className="py-4 px-4">
                       <span className={`px-2 py-1 rounded text-xs font-bold ${item.priority === 'HIGH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-orange-500/20 text-orange-400'}`}>
                         {item.priority}
                       </span>
                    </td>
                    <td className="py-4 px-4 text-sm text-slate-300">{item.status}</td>
                    <td className="py-4 px-4">
                      <button onClick={() => handleRemove(item.id)} className="text-slate-400 hover:text-red-500 transition-colors p-2 bg-slate-900 rounded-lg hover:bg-red-500/10">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {watchlist.length === 0 && (
                  <tr>
                    <td colSpan="5" className="py-12 text-center text-slate-500">No active targets found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
