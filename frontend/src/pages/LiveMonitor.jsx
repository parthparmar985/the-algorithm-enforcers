import { backendUrl } from '../services/endpoints';
import { useState, useEffect, useMemo, useRef } from 'react';
import { getCameras } from '../services/cameraService';
import { startLiveInference } from '../services/videoService';
import { Activity, Signal, MapPin, Search, X, Maximize, Minimize } from 'lucide-react';
import './LiveMonitor.css';

const normalizeName = value => (value || '').trim().replace(/\s+/g, ' ').toLowerCase();
const healthColors = { ONLINE: 'text-green-400', DEGRADED: 'text-amber-300', OFFLINE: 'text-red-400' };

export default function LiveMonitor() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [fullscreenId, setFullscreenId] = useState(null);
  const [fullscreenError, setFullscreenError] = useState('');
  const [fullscreenPending, setFullscreenPending] = useState(false);
  const fullscreenBusy = useRef(false);
  const wallRef = useRef(null);
  const visibleIds = useMemo(() => {
    const query = normalizeName(search);
    return new Set(cameras
      .filter(cam => normalizeName(cam.camera_name).includes(query))
      .map(cam => cam.id));
  }, [cameras, search]);

  useEffect(() => {
    let disposed = false;
    let timer;
    const fetchCameras = async () => {
      try {
        const data = await getCameras();
        if (!disposed) setCameras(data.filter(c => c.status === 'ONLINE'));
      } catch {
        if (!disposed) console.error('Failed to fetch cameras');
      } finally {
        if (!disposed) {
          setLoading(false);
          // Refresh metadata only; never probe streams or start inference here.
          timer = window.setTimeout(fetchCameras, 30000);
        }
      }
    };
    fetchCameras();
    return () => { disposed = true; window.clearTimeout(timer); };
  }, []);

  useEffect(() => {
    const wall = wallRef.current;
    const syncFullscreen = () => {
      const element = document.fullscreenElement;
      setFullscreenId(element && wall?.contains(element) ? element.dataset.cameraId : null);
      setFullscreenError('');
    };
    document.addEventListener('fullscreenchange', syncFullscreen);
    syncFullscreen();
    return () => {
      document.removeEventListener('fullscreenchange', syncFullscreen);
      if (document.fullscreenElement && wall?.contains(document.fullscreenElement)) {
        document.exitFullscreen?.().catch(() => {});
      }
    };
  }, []);

  const toggleFullscreen = async (event) => {
    if (fullscreenBusy.current) return;
    const card = event.currentTarget.closest('[data-camera-id]');
    fullscreenBusy.current = true;
    setFullscreenPending(true);
    setFullscreenError('');
    try {
      if (document.fullscreenElement === card) {
        await document.exitFullscreen();
      } else {
        if (!card.requestFullscreen) throw new Error('Fullscreen unavailable');
        await card.requestFullscreen();
      }
    } catch {
      setFullscreenError('Unable to change fullscreen. The feed is still active. Try again or press Esc to exit.');
    } finally {
      fullscreenBusy.current = false;
      setFullscreenPending(false);
    }
  };

  return (
    <div ref={wallRef} className="p-4 md:p-8 text-white max-w-[1600px] mx-auto min-h-screen bg-transparent">
      
      {/* Header */}
      <div className="bg-slate-800/80 backdrop-blur-xl p-6 rounded-3xl shadow-2xl border border-slate-700/50 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center tracking-tight">
            <Activity className="text-red-500 w-8 h-8 mr-3 animate-pulse" /> LIVE VIDEO WALL
          </h1>
          <p className="text-slate-400 text-sm mt-1">Real-time dynamic monitoring of {cameras.length} connected endpoints.</p>
        </div>
        <div className="w-full md:max-w-md">
          <div className="relative">
            <Search aria-hidden="true" className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
            <input type="search" aria-label="Search cameras by name" placeholder="Search cameras by name..."
              value={search} onChange={event => setSearch(event.target.value)}
              className="w-full bg-slate-900/80 border border-slate-600 rounded-xl pl-10 pr-12 py-2.5 text-slate-200 focus:outline-none focus:border-blue-500" />
            {search && <button type="button" aria-label="Clear camera search" onClick={() => setSearch('')}
              className="absolute right-1 top-1 p-2 text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>}
          </div>
          <p role="status" className="text-sm text-slate-400 mt-2">Showing {visibleIds.size} of {cameras.length} cameras</p>
        </div>
      </div>

      {fullscreenError && <p role="alert" className="mb-4 text-amber-300">{fullscreenError}</p>}

      {loading ? (
        <div className="flex justify-center items-center h-64 text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500 mr-3"></div>
          Connecting to video streams...
        </div>
      ) : (
        <>
          {visibleIds.size === 0 && (
            <div className="py-24 text-center bg-slate-800/30 rounded-3xl border-dashed border-2 border-slate-700 flex flex-col items-center justify-center">
              <Signal className="w-16 h-16 text-slate-600 mb-4 opacity-50" />
              <h3 className="text-xl font-bold text-slate-400">No cameras found</h3>
              <p className="text-slate-500 mt-2">{normalizeName(search) ? 'Try another camera name.' : 'Make sure at least one camera is registered and marked ONLINE.'}</p>
            </div>
          )}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {/* Keep every stream mounted with a stable key and src, even for zero matches. */}
              {cameras.map((cam) => (
                <div key={cam.id} data-camera-id={cam.id} style={{ display: visibleIds.has(cam.id) || fullscreenId === String(cam.id) ? undefined : 'none' }} className="live-camera-card bg-slate-900 rounded-2xl border border-slate-700 overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.5)] group relative flex flex-col aspect-video">
                  
                  {/* MJPEG Stream Viewer */}
                  <div className="live-camera-feed absolute inset-0 bg-black flex items-center justify-center z-0">
                    {/* The API directly yields an MJPEG stream, so an img tag loops beautifully */}
                    <img 
                      src={`${backendUrl}/api/video/${cam.id}/stream`}
                      alt={`Live ${cam.camera_code}`}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  </div>

                  {/* Overlays / Tag Lines */}
                  <div className="live-camera-header absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent z-10 flex justify-between items-start gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]"></span>
                        <span className="font-bold tracking-widest uppercase text-white drop-shadow-md">CAM-{cam.camera_code}</span>
                      </div>
                      <h3 className="font-medium text-slate-300 text-sm mt-1 drop-shadow-md">{cam.camera_name}</h3>
                    </div>
                    
                    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
                      <button type="button" onClick={toggleFullscreen} disabled={fullscreenPending}
                        aria-label={`${fullscreenId === String(cam.id) ? 'Exit fullscreen' : 'Enter fullscreen'} for ${cam.camera_name}`}
                        title={fullscreenId === String(cam.id) ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
                        className="col-start-2 row-start-1 p-2 rounded-lg bg-black/60 border border-white/20 hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-blue-400 disabled:opacity-50">
                        {fullscreenId === String(cam.id) ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
                      </button>
                      <div className="col-start-1 row-start-1 px-3 py-1 bg-black/50 backdrop-blur-md border border-white/10 rounded-lg flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-blue-400" />
                        <span className="text-xs font-semibold tracking-wide text-blue-100">{cam.location || 'Unknown Location'}</span>
                      </div>
                      <button 
                        onClick={() => {
                          startLiveInference(cam.id)
                            .then(() => alert(`Live AI Engine Activated for CAM-${cam.camera_code}! Keep watching for Watchlist Alerts.`))
                            .catch((err) => alert('Failed to start engine: ' + (err.response?.data?.detail || err.message)));
                        }}
                        className="col-span-2 justify-self-end px-3 py-1.5 mt-1 bg-indigo-600/90 hover:bg-indigo-500 text-white text-[10px] font-bold rounded shadow-lg tracking-wider border border-indigo-400 transition-colors"
                      >
                        ACTIVATE AI ENGINE
                      </button>
                    </div>
                  </div>
                  <div className="live-camera-health absolute bottom-0 inset-x-0 px-4 py-2 bg-black/70 z-10 flex flex-wrap justify-between gap-2 text-xs font-semibold">
                    <span className={healthColors[cam.health_status] || 'text-slate-300'}>{cam.health_status || 'UNKNOWN'}</span>
                    <span>Processing: {Number.isFinite(cam.runtime_health?.processing_fps) ? cam.runtime_health.processing_fps.toFixed(1) : '—'} FPS</span>
                    {fullscreenError && fullscreenId === String(cam.id) && <p role="alert" className="w-full text-amber-300">{fullscreenError}</p>}
                  </div>
                </div>
              ))}
            </div>
        </>
      )}
    </div>
  );
}
