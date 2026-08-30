import { useState, useEffect } from 'react';
import { getCameras, createCamera, deleteCamera, updateCamera } from '../services/cameraService';
import { startLiveInference } from '../services/videoService';
import { useAuth } from '../context/AuthContext';
import { Plus, Trash2, Edit, Camera as CamIcon, Search, Filter, Signal, MapPin, X, Brain } from 'lucide-react';

export default function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [editingCamera, setEditingCamera] = useState(null);
  const [filteredCameras, setFilteredCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  
  const { user } = useAuth();
  
  const [formData, setFormData] = useState({
    camera_name: '', camera_code: '', location: '', stream_url: '', status: 'OFFLINE'
  });

  useEffect(() => {
    fetchCameras();
  }, []);

  useEffect(() => {
    let result = cameras;
    if (statusFilter !== 'ALL') {
      result = result.filter(c => c.status === statusFilter);
    }
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(c => 
        c.camera_name.toLowerCase().includes(term) || 
        c.camera_code.toLowerCase().includes(term) || 
        (c.location && c.location.toLowerCase().includes(term))
      );
    }
    setFilteredCameras(result);
  }, [cameras, searchTerm, statusFilter]);

  const fetchCameras = async () => {
    try {
      const data = await getCameras();
      setCameras(data);
    } catch (error) {
      console.error("Failed to fetch cameras");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await createCamera({
        ...formData
      });
      setFormData({ camera_name: '', camera_code: '', location: '', stream_url: '', status: 'OFFLINE'});
      fetchCameras();
    } catch (err) {
      console.error("Failed to create camera");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this camera?")) return;
    try {
      await deleteCamera(id);
      fetchCameras();
    } catch (err) {
      console.error("Failed to delete camera");
    }
  };

  const handleStartLiveAI = async (id) => {
    try {
      await startLiveInference(id);
      alert("SUCCESS: Live continuous Machine Learning inference has been activated for this camera! Check View Records for extractions.");
    } catch (err) {
      alert("Failed to start AI. Ensure Stream URL is valid.");
    }
  }

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await updateCamera(editingCamera.id, {
        camera_name: editingCamera.camera_name,
        camera_code: editingCamera.camera_code,
        location: editingCamera.location,
        stream_url: editingCamera.stream_url,
        status: editingCamera.status
      });
      setEditingCamera(null);
      fetchCameras();
    } catch (err) {
      console.error("Failed to update camera");
    }
  };

  return (
    <div className="p-4 md:p-8 text-white max-w-[1600px] mx-auto min-h-screen bg-transparent">
      
      {/* Header & Controls */}
      <div className="bg-slate-800/80 backdrop-blur-xl p-6 rounded-3xl shadow-2xl border border-slate-700/50 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center tracking-tight">
            <CamIcon className="text-blue-500 w-8 h-8 mr-3" /> CCTV NETWORK
          </h1>
          <p className="text-slate-400 text-sm mt-1">Manage and monitor {cameras.length} integrated endpoints.</p>
        </div>
        
        <div className="flex w-full md:w-auto gap-4">
          <div className="relative flex-1 md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-500" />
            </div>
            <input
              type="text"
              placeholder="Search cameras..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-600 rounded-xl pl-10 pr-4 py-2.5 text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Filter className="h-5 w-5 text-slate-500" />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900/80 border border-slate-600 rounded-xl pl-10 pr-8 py-2.5 text-slate-200 focus:outline-none focus:border-blue-500 transition-colors appearance-none cursor-pointer"
            >
              <option value="ALL">All Status</option>
              <option value="ONLINE">Online</option>
              <option value="OFFLINE">Offline</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        
        {/* Admin Create Form */}
        {user?.role === 'ADMIN' && (
          <div className="xl:col-span-1 bg-slate-800/80 p-6 rounded-3xl border border-slate-700/50 h-fit shadow-xl">
            <h2 className="text-xl font-bold mb-6 flex items-center"><Plus className="w-5 h-5 mr-2 text-blue-400" /> Provision Node</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">CAMERA NAME</label>
                <input required type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={formData.camera_name} onChange={e => setFormData({...formData, camera_name: e.target.value})} placeholder="Main Gate Cam" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                 <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">CODE</label>
                  <input required type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={formData.camera_code} onChange={e => setFormData({...formData, camera_code: e.target.value})} placeholder="CAM-01" />
                 </div>
                 <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">STATUS</label>
                  <select className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})}>
                    <option value="OFFLINE">Offline</option>
                    <option value="ONLINE">Online</option>
                  </select>
                 </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">LOCATION DESCRIPTION</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} placeholder="North Ring Road" />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">STREAM URL</label>
                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={formData.stream_url} onChange={e => setFormData({...formData, stream_url: e.target.value})} placeholder="rtsp:// or http:// video feed" />
              </div>
              <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 p-3 rounded-xl font-bold mt-4 shadow-[0_0_15px_rgba(59,130,246,0.5)] transition-all">
                Connect Camera
              </button>
            </form>
          </div>
        )}

        {/* Camera Grid Network */}
        <div className={user?.role === 'ADMIN' ? 'xl:col-span-3' : 'xl:col-span-4'}>
          {loading ? (
            <div className="flex justify-center items-center h-64 text-slate-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-3"></div>
              Synchronizing Network...
            </div>
          ) : (
            <>
              {filteredCameras.length === 0 ? (
                <div className="py-24 text-center bg-slate-800/30 rounded-3xl border-dashed border-2 border-slate-700 flex flex-col items-center justify-center">
                  <Signal className="w-16 h-16 text-slate-600 mb-4 opacity-50" />
                  <h3 className="text-xl font-bold text-slate-400">0 Nodes Verified</h3>
                  <p className="text-slate-500 mt-2">Adjust search/filters or deploy a new camera.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredCameras.map((cam) => (
                    <div key={cam.id} className="bg-slate-800/60 p-5 rounded-2xl border border-slate-700/50 shadow-lg hover:border-blue-500/30 hover:bg-slate-800/90 transition-all flex flex-col relative group overflow-hidden">
                      {/* Top Bar */}
                      <div className="flex justify-between items-start mb-4">
                        <div>
                           <span className="font-mono text-xs font-bold text-slate-400 bg-slate-900 px-2 py-1 rounded">CAM-{cam.camera_code}</span>
                           <h3 className="font-bold text-lg text-slate-100 mt-2 truncate w-full">{cam.camera_name}</h3>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                           <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase flex items-center gap-1 ${cam.status === 'ONLINE' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-700 text-slate-400 border border-slate-600'}`}>
                             {cam.status === 'ONLINE' && <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>}
                             {cam.status}
                           </span>
                           {/* Status Badge */}
                        </div>
                      </div>
                      
                      {/* Live Feed Preview Box */}
                      <div className="w-full h-40 bg-slate-950 rounded-xl mb-4 mt-2 overflow-hidden border border-slate-700/50 shadow-inner relative flex justify-center items-center group-hover:border-blue-500/50 transition-all">
                         {cam.status === 'ONLINE' ? (
                            <>
                               <img src={`http://localhost:8000/api/video/${cam.id}/stream`} alt={`Stream ${cam.camera_code}`} className="w-full h-full object-cover opacity-90" />
                               <div className="absolute top-2 left-2 bg-red-600/90 text-white text-[9px] font-bold px-2 py-0.5 rounded shadow-lg flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span> REC</div>
                            </>
                         ) : (
                            <div className="flex flex-col items-center justify-center text-slate-500">
                               <CamIcon className="w-8 h-8 mb-2 opacity-30" />
                               <span className="text-[10px] font-mono tracking-widest font-bold">STREAM UNAVAILABLE</span>
                            </div>
                         )}
                      </div>
                      
                      {/* Details */}
                      <div className="space-y-2 text-sm text-slate-400 mt-2">
                        <div className="flex items-center justify-between border-t border-slate-700/30 pt-3">
                           <div className="flex items-center gap-2">
                              <MapPin className="w-4 h-4 text-blue-400/50" />
                              <span className="truncate text-xs font-bold">{cam.location || 'Unknown Location'}</span>
                           </div>
                           <div className="flex items-center gap-2">
                              <Signal className="w-4 h-4 text-blue-400/50" />
                              <span className="truncate font-mono text-[9px] uppercase font-bold text-slate-500">
                                 {cam.stream_url ? 'RTSP ACTIVE' : 'NO URL'}
                              </span>
                           </div>
                        </div>
                      </div>

                      {/* Explicit Admin Controls Bar */}
                      {user?.role === 'ADMIN' && (
                        <div className="mt-4 pt-3 border-t border-slate-700/50 flex flex-col -mx-5 -mb-5 px-5 py-3 bg-slate-900/50 gap-2">
                           
                           {/* Primary AI Activation Action */}
                           <button onClick={() => handleStartLiveAI(cam.id)} className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white px-3 py-2 rounded-lg flex items-center justify-center text-[11px] font-bold tracking-widest transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)]">
                             <Brain className="w-4 h-4 mr-2" /> ACTIVATE AI RUNTIME
                           </button>

                           {/* Secondary Config Controls */}
                           <div className="flex gap-2 mt-1">
                               <button onClick={() => setEditingCamera(cam)} className="flex-1 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 px-3 py-1.5 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all border border-blue-500/20 hover:border-blue-500/50">
                                  <Edit className="w-3 h-3 mr-1.5" /> VERIFY
                               </button>
                               <button onClick={() => handleDelete(cam.id)} className="flex-1 bg-red-600/20 hover:bg-red-600/40 text-red-400 px-3 py-1.5 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all border border-red-500/20 hover:border-red-500/50">
                                  <Trash2 className="w-3 h-3 mr-1.5" /> TERMINATE
                               </button>
                           </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

      </div>

      {/* Edit Camera Modal */}
      {editingCamera && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700/50 rounded-3xl p-6 w-full max-w-lg shadow-[0_0_40px_rgba(0,0,0,0.8)] animate-enter relative">
            <button onClick={() => setEditingCamera(null)} className="absolute top-6 right-6 text-slate-500 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
            <h2 className="text-xl font-bold mb-6 flex items-center"><Edit className="w-5 h-5 mr-2 text-blue-400" /> Edit Node Configuration</h2>
            
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">CAMERA NAME</label>
                <input required type="text" className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={editingCamera.camera_name} onChange={e => setEditingCamera({...editingCamera, camera_name: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                 <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">CODE</label>
                  <input required type="text" className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={editingCamera.camera_code} onChange={e => setEditingCamera({...editingCamera, camera_code: e.target.value})} />
                 </div>
                 <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">STATUS</label>
                  <select className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={editingCamera.status} onChange={e => setEditingCamera({...editingCamera, status: e.target.value})}>
                    <option value="OFFLINE">Offline</option>
                    <option value="ONLINE">Online</option>
                  </select>
                 </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">LOCATION DESCRIPTION</label>
                <input type="text" className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={editingCamera.location || ''} onChange={e => setEditingCamera({...editingCamera, location: e.target.value})} />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">STREAM URL</label>
                <input type="text" className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 px-3 text-slate-200 focus:outline-none focus:border-blue-500" value={editingCamera.stream_url || ''} onChange={e => setEditingCamera({...editingCamera, stream_url: e.target.value})} />
              </div>
              <div className="pt-4 flex gap-3">
                <button type="button" onClick={() => setEditingCamera(null)} className="flex-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded-xl font-bold transition-all">Cancel</button>
                <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-500 p-3 rounded-xl font-bold shadow-[0_0_15px_rgba(59,130,246,0.5)] transition-all">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
