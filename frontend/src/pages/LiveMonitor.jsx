import { useState, useEffect } from 'react';
import { getCameras } from '../services/cameraService';
import { Activity, Signal, MapPin } from 'lucide-react';

export default function LiveMonitor() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      const data = await getCameras();
      setCameras(data.filter(c => c.status === 'ONLINE'));
    } catch (error) {
      console.error("Failed to fetch cameras");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-8 text-white max-w-[1600px] mx-auto min-h-screen bg-transparent">
      
      {/* Header */}
      <div className="bg-slate-800/80 backdrop-blur-xl p-6 rounded-3xl shadow-2xl border border-slate-700/50 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center tracking-tight">
            <Activity className="text-red-500 w-8 h-8 mr-3 animate-pulse" /> LIVE VIDEO WALL
          </h1>
          <p className="text-slate-400 text-sm mt-1">Real-time dynamic monitoring of {cameras.length} connected endpoints.</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64 text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500 mr-3"></div>
          Connecting to video streams...
        </div>
      ) : (
        <>
          {cameras.length === 0 ? (
            <div className="py-24 text-center bg-slate-800/30 rounded-3xl border-dashed border-2 border-slate-700 flex flex-col items-center justify-center">
              <Signal className="w-16 h-16 text-slate-600 mb-4 opacity-50" />
              <h3 className="text-xl font-bold text-slate-400">0 Live Feeds Found</h3>
              <p className="text-slate-500 mt-2">Make sure at least one camera is registered and marked ONLINE.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {cameras.map((cam) => (
                <div key={cam.id} className="bg-slate-900 rounded-2xl border border-slate-700 overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.5)] group relative flex flex-col aspect-video">
                  
                  {/* MJPEG Stream Viewer */}
                  <div className="absolute inset-0 bg-black flex items-center justify-center z-0">
                    {/* The API directly yields an MJPEG stream, so an img tag loops beautifully */}
                    <img 
                      src={`http://localhost:8000/api/video/${cam.id}/stream`}
                      alt={`Live ${cam.camera_code}`}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  </div>

                  {/* Overlays / Tag Lines */}
                  <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent z-10 flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]"></span>
                        <span className="font-bold tracking-widest uppercase text-white drop-shadow-md">CAM-{cam.camera_code}</span>
                      </div>
                      <h3 className="font-medium text-slate-300 text-sm mt-1 drop-shadow-md">{cam.camera_name}</h3>
                    </div>
                    
                    <div className="px-3 py-1 bg-black/50 backdrop-blur-md border border-white/10 rounded-lg flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-xs font-semibold tracking-wide text-blue-100">{cam.location || 'Unknown Location'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
