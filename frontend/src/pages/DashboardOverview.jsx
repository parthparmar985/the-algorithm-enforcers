import { useState, useEffect } from 'react';
import { getAnalyticsSummary } from '../services/dataService';
import { Camera, Activity, AlertTriangle, Car } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardOverview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const timer = window.setInterval(fetchData, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const fetchData = async () => {
    try {
      const result = await getAnalyticsSummary();
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center p-8 text-white min-h-screen bg-transparent max-w-7xl mx-auto"><div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>;
  if (!data) return <div className="p-8 text-red-400 min-h-screen bg-transparent max-w-7xl mx-auto font-medium">Error loading intelligence analytics. Make sure the backend server (FastAPI) is running.</div>;

  // Add optional chaining and fallback
  const vehicleObj = data?.charts?.vehicle_types || {};
  const chartData = Object.entries(vehicleObj).map(([key, val]) => ({
    name: (key || 'UNKNOWN').toUpperCase(), count: val
  }));
  const health = data.camera_health || { total: data.summary.total_cameras, online: data.summary.online_cameras, degraded: 0, offline: 0, unknown: 0 };

  return (
    <div className="p-4 md:p-8 text-slate-200 min-h-screen bg-transparent max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-8 tracking-tight text-white drop-shadow-md">Command Center Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <div className="glass-card p-6 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-xl group-hover:bg-blue-500/20 transition-all"></div>
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-slate-400 font-medium tracking-wide">Cameras</h3>
            <Camera className="text-blue-400 w-6 h-6" />
          </div>
          <p className="text-4xl font-bold">{data.summary.online_cameras} <span className="text-sm text-slate-500 font-normal">/ {data.summary.total_cameras} Online</span></p>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-slate-400 font-medium tracking-wide">Today Detections</h3>
            <Activity className="text-indigo-400 w-6 h-6" />
          </div>
          <p className="text-4xl font-bold">{data.summary.today_detections}</p>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-slate-400 font-medium tracking-wide">Plates Read</h3>
            <Car className="text-emerald-400 w-6 h-6" />
          </div>
          <p className="text-4xl font-bold">{data.summary.plates_detected}</p>
        </div>
        
        <div className="glass-card p-6 rounded-3xl relative overflow-hidden border border-red-500/20 group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-2xl group-hover:bg-red-500/20 transition-all"></div>
          <div className="flex justify-between items-start mb-2 relative z-10">
            <h3 className="text-red-200 font-medium tracking-wide">Critical Alerts</h3>
            <AlertTriangle className="text-red-500 w-6 h-6 animate-pulse" />
          </div>
          <p className="text-4xl font-bold text-red-400">{data.summary.critical_alerts}</p>
        </div>
      </div>

      <div className="glass-card p-6 rounded-3xl mb-12 border border-slate-700/60">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2"><Camera className="w-5 h-5 text-blue-400" />Camera Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[['Total', health.total, 'text-white'], ['Online', health.online, 'text-emerald-400'], ['Degraded', health.degraded, 'text-amber-400'], ['Offline', health.offline, 'text-red-400'], ['Unknown', health.unknown, 'text-slate-400']].map(([label, value, color]) => <div key={label} className="bg-slate-900/60 border border-slate-700 rounded-xl p-4"><p className="text-xs uppercase tracking-wider text-slate-500">{label}</p><p className={`text-3xl font-bold ${color}`}>{value}</p></div>)}
        </div>
        <p className="text-xs text-slate-500 mt-3">Health counts reflect measured stream reachability and valid frames, independent of configured camera status.</p>
      </div>

      <div className="glass-card p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute -bottom-20 -left-20 w-64 h-64 bg-blue-500/10 rounded-full blur-[80px] pointer-events-none"></div>
        <h3 className="text-xl font-bold mb-8 text-white relative z-10">Traffic Classification</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip cursor={{fill: '#334155'}} contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
