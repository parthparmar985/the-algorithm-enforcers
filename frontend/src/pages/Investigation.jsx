import { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Search, MapPin, Clock, AlertTriangle, CheckCircle, Navigation } from 'lucide-react';
import L from 'leaflet';

// Fix leaflet default icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

import api from '../services/api';

const getImageUrl = (path) => {
  if (!path) return 'https://via.placeholder.com/300?text=No+Snapshot';
  if (path.startsWith('http')) return path;
  let cleanPath = path.replace(/\\/g, '/');
  if (cleanPath.startsWith('uploads/')) {
    cleanPath = '/static/' + cleanPath.substring(8);
  } else if (!cleanPath.startsWith('/')) {
    cleanPath = '/' + cleanPath;
  }
  return `http://localhost:8000${cleanPath}`;
};

export default function Investigation() {
  const [queryStr, setQueryStr] = useState('');
  const [traceResults, setTraceResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleTrace = async (e) => {
    e.preventDefault();
    if (!queryStr) return;
    setLoading(true);
    setSearched(true);
    try {
      // Hit the new trace API
      const response = await api.get(`/search/trace/${queryStr}`);
      setTraceResults(response.data);
    } catch (err) {
      console.error(err);
      setTraceResults([]);
    } finally {
      setLoading(false);
    }
  };

  // Compute map bounds or default center
  const mapCenter = traceResults.length > 0 && traceResults[0].latitude
    ? [traceResults[0].latitude, traceResults[0].longitude]
    : [28.6139, 77.2090]; // Default India (Delhi)

  const positions = traceResults
    .filter(t => t.latitude && t.longitude)
    .map(t => [t.latitude, t.longitude]);

  return (
    <div className="p-4 md:p-8 text-white max-w-[1400px] mx-auto min-h-screen bg-transparent">
      
      {/* Search Header */}
      <div className="bg-slate-800/80 backdrop-blur-xl p-6 md:p-8 rounded-3xl border border-slate-700/50 shadow-2xl mb-8">
        <div className="flex flex-col md:flex-row gap-6 items-start md:items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight mb-2">AI VEHICLE INVESTIGATION</h1>
            <p className="text-slate-400 text-sm">Enter Registration Number to trace vehicle across integrated CCTV network.</p>
          </div>
          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50 flex gap-8">
             <div>
               <p className="text-xs text-slate-500 font-bold tracking-wider mb-1">FIRST SEEN</p>
               <p className="text-lg font-mono font-bold text-slate-200">
                 {traceResults.length > 0 ? new Date(traceResults[0].timestamp).toLocaleTimeString() : '--:--:--'}
               </p>
             </div>
             <div>
               <p className="text-xs text-slate-500 font-bold tracking-wider mb-1">LAST SEEN</p>
               <p className="text-lg font-mono font-bold text-slate-200">
                 {traceResults.length > 0 ? new Date(traceResults[traceResults.length - 1].timestamp).toLocaleTimeString() : '--:--:--'}
               </p>
             </div>
             <div>
               <p className="text-xs text-slate-500 font-bold tracking-wider mb-1">TOTAL SIGHTINGS</p>
               <p className="text-lg font-mono font-bold text-indigo-400">
                 {traceResults.length}
               </p>
             </div>
          </div>
        </div>

        <form onSubmit={handleTrace} className="flex gap-4 items-end">
          <div className="flex-1 relative">
            <input 
              type="text" 
              value={queryStr}
              onChange={(e) => setQueryStr(e.target.value.toUpperCase())}
              placeholder="e.g. GJ01AB1234"
              className="w-full bg-slate-900/80 border-2 border-slate-600 rounded-xl p-5 text-xl font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 transition-all uppercase"
            />
          </div>
          <button type="submit" disabled={loading || !queryStr} className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 p-5 rounded-xl flex items-center justify-center font-bold text-lg shadow-xl shadow-indigo-500/25 transition-all hover:-translate-y-1 min-w-[200px] disabled:opacity-50 disabled:cursor-not-allowed border border-indigo-400/20">
            {loading ? <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <><Navigation className="w-6 h-6 mr-3" /> TRACE VEHICLE</>}
          </button>
        </form>
      </div>

      {(!searched && traceResults.length === 0) && (
        <div className="flex flex-col items-center justify-center h-64 text-slate-500 border-2 border-slate-700/50 border-dashed rounded-3xl bg-slate-800/30">
          <Search className="w-16 h-16 mb-4 opacity-50" />
          <h2 className="text-2xl font-bold mb-2 text-slate-400">Initiate Trace</h2>
          <p>Enter a vehicle registration plate above to plot its chronological route.</p>
        </div>
      )}

      {(searched && traceResults.length === 0 && !loading) && (
        <div className="p-8 text-center bg-red-900/20 border border-red-500/30 rounded-3xl">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-red-400">NO RECORDS FOUND</h2>
          <p className="text-slate-400 mt-2">Vehicle has not been sighted by any integrated camera.</p>
        </div>
      )}

      {traceResults.length > 0 && (
        <>
          {/* Middle Layout: Map + Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
            
            {/* ROUTE MAP */}
            <div className="lg:col-span-2 bg-slate-800/80 backdrop-blur-xl rounded-3xl border border-slate-700/50 shadow-2xl overflow-hidden flex flex-col h-[600px]">
              <div className="p-5 flex items-center justify-between border-b border-slate-700/50 bg-slate-900/30">
                <h3 className="font-bold text-lg flex items-center"><MapPin className="w-5 h-5 mr-3 text-indigo-400" /> ROUTE MAP</h3>
                <span className="bg-indigo-500/20 text-indigo-300 text-xs px-3 py-1 rounded-full border border-indigo-500/30 font-bold tracking-widest">{queryStr}</span>
              </div>
              <div className="flex-1 bg-slate-900 relative">
                <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%', zIndex: 10 }}>
                  <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution="&copy; OpenStreetMap contributors"
                  />
                  {positions.length > 1 && (
                    <Polyline positions={positions} color="#6366f1" weight={4} dashArray="10, 10" className="animate-pulse" />
                  )}
                  {traceResults.map((item, index) => (
                    item.latitude && item.longitude && (
                      <Marker key={item.id} position={[item.latitude, item.longitude]}>
                        <Popup className="custom-popup">
                          <div className="text-slate-800 p-1">
                            <p className="font-bold text-lg">{index + 1}. CAM-{item.camera_code}</p>
                            <p className="text-sm font-semibold">{item.location}</p>
                            <p className="text-xs text-slate-500 mt-1">{new Date(item.timestamp).toLocaleString()}</p>
                          </div>
                        </Popup>
                      </Marker>
                    )
                  ))}
                </MapContainer>
              </div>
            </div>

            {/* TIMELINE */}
            <div className="bg-slate-800/80 backdrop-blur-xl rounded-3xl border border-slate-700/50 shadow-2xl h-[600px] flex flex-col">
              <div className="p-5 border-b border-slate-700/50 bg-slate-900/30">
                <h3 className="font-bold text-lg flex items-center"><Clock className="w-5 h-5 mr-3 text-indigo-400" /> MOVEMENT TIMELINE</h3>
              </div>
              <div className="p-6 overflow-y-auto flex-1 space-y-6 custom-scrollbar">
                {traceResults.map((item, index) => (
                  <div key={item.id} className="relative pl-8">
                    {/* Timeline Line */}
                    {index !== traceResults.length - 1 && (
                      <div className="absolute top-8 left-3 w-0.5 h-full bg-slate-700 -ml-[0.5px]"></div>
                    )}
                    
                    {/* Timeline Dot */}
                    <div className="absolute top-1 left-0 w-6 h-6 rounded-full bg-indigo-600 border-4 border-slate-800 flex items-center justify-center text-[10px] font-bold shadow-[0_0_10px_rgba(79,70,229,0.5)]">
                      {index + 1}
                    </div>
                    
                    <div className={`p-4 rounded-2xl border ${item.transition_status === 'ANOMALOUS TRANSITION' ? 'bg-red-900/10 border-red-500/30' : 'bg-slate-900/50 border-slate-700/50'}`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-mono text-lg font-bold text-slate-200">{new Date(item.timestamp).toLocaleTimeString()}</span>
                        <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400 font-mono">CAM-{item.camera_code}</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-300 mb-1 line-clamp-1">{item.location}</p>
                      
                      <div className="flex items-center gap-2 mt-3 text-xs">
                        <span className="bg-green-900/30 text-green-400 border border-green-500/20 px-2 py-0.5 rounded font-bold">{Math.round(item.confidence * 100)}% Match</span>
                        <span className="text-slate-500 uppercase">{item.vehicle_type}</span>
                      </div>

                      {item.transition_status !== 'STARTPOINT' && (
                        <div className={`mt-4 text-xs font-semibold p-2 rounded-lg flex items-center gap-2 ${item.transition_status === 'ANOMALOUS TRANSITION' ? 'bg-red-500/20 text-red-300' : 'bg-blue-500/10 text-blue-300'}`}>
                          {item.transition_status === 'ANOMALOUS TRANSITION' ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                          {item.distance_km}km in {item.time_diff_mins}m 
                          <span className="ml-auto bg-black/30 px-1 py-0.5 rounded opacity-70">
                            {item.transition_status.split(' ')[0]}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* BOTTOM: EVIDENCE BOARD */}
          <div className="bg-slate-800/80 backdrop-blur-xl p-6 md:p-8 rounded-3xl border border-slate-700/50 shadow-2xl">
             <h3 className="font-bold text-xl mb-6 flex items-center"><Search className="w-5 h-5 mr-3 text-indigo-400" /> EVIDENCE BOARD</h3>
             <div className="flex overflow-x-auto gap-6 pb-4 custom-scrollbar">
                {traceResults.map((item, index) => (
                  <div key={item.id} className="min-w-[280px] bg-slate-900 rounded-2xl border border-slate-700 overflow-hidden flex flex-col group hover:border-indigo-500/50 transition-colors">
                    <div className="relative h-40 bg-slate-950 overflow-hidden">
                      <img 
                        src={getImageUrl(item.snapshot_path)} 
                        alt="Evidence" 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => e.target.src = 'https://via.placeholder.com/300?text=No+Snapshot'}
                      />
                      <div className="absolute top-2 right-2 bg-black/70 backdrop-blur text-white text-xs font-bold px-2 py-1 rounded-lg">
                        #{index + 1}
                      </div>
                    </div>
                    <div className="p-4">
                      <div className="flex justify-between items-center mb-1">
                        <p className="font-mono font-bold text-indigo-300">{queryStr}</p>
                        <p className="text-xs text-slate-500">{new Date(item.timestamp).toLocaleTimeString()}</p>
                      </div>
                      <p className="text-xs text-slate-400">CAM-{item.camera_code} • {item.location}</p>
                    </div>
                  </div>
                ))}
             </div>
          </div>
        </>
      )}

    </div>
  );
}
