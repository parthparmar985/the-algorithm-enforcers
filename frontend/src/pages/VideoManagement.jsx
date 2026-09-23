import { useState, useEffect } from 'react';
import { uploadVideo, startProcessing } from '../services/videoService';
import { getCameras } from '../services/cameraService';
import { searchVehicles } from '../services/dataService';
import { Video, Upload, ServerCog, CheckCircle, ChevronRight, Activity, Car, ScanLine, Clock, Hash, Search, X, FileText } from 'lucide-react';

const fallbackImage = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><rect fill="%231e293b" width="300" height="200"/><text fill="%2364748b" font-family="monospace" font-size="20" font-weight="bold" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">NO SNAPSHOT</text></svg>`;

const getImageUrl = (path) => {
  if (!path) return fallbackImage;
  if (path.startsWith('http')) return path;
  let cleanPath = path.replace(/\\/g, '/');
  if (cleanPath.startsWith('uploads/')) {
    cleanPath = '/static/' + cleanPath.substring(8);
  } else if (!cleanPath.startsWith('/static/')) {
    cleanPath = cleanPath.startsWith('/') ? `/static${cleanPath}` : `/static/${cleanPath}`;
  }
  return `http://localhost:8000${cleanPath}`;
};

export default function VideoManagement() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [processingStatus, setProcessingStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [activeRecord, setActiveRecord] = useState(null);

  useEffect(() => {
    fetchCameras();
    const ws = new WebSocket('ws://localhost:8000/ws/alerts');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'PROGRESS') {
          setProgress(data.percentage);
          if (data.percentage >= 100) {
            setProcessingStatus('Completed & Analyzed.');
            setIsProcessing(false);
            // Fetch the details automatically to show them in the sidebar
            if (window.__selectedCameraIdForSocket) {
               searchVehicles({ camera_id: window.__selectedCameraIdForSocket }).then(res => {
                  setAnalysisResults(res);
               }).catch(e => console.error(e));
            }
          } else {
            setIsProcessing(true);
            setProcessingStatus(`Engine Active... ${data.percentage}%`);
          }
        }
      } catch (err) {}
    };
    return () => ws.close();
  }, []);

  const fetchCameras = async () => {
    try {
      const data = await getCameras();
      setCameras(data);
      if (data.length > 0) setSelectedCameraId(data[0].id);
      else setSelectedCameraId(1);
    } catch (err) {
      console.error(err);
      setSelectedCameraId(1);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setUploading(true);
    try {
      const res = await uploadVideo(file);
      setUploadResult(res);
      setFile(null);
    } catch (err) {
      console.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async () => {
    if (!uploadResult || !selectedCameraId) return;
    
    try {
      setProcessingStatus('Starting AI process...');
      window.__selectedCameraIdForSocket = selectedCameraId;
      const res = await startProcessing(selectedCameraId, uploadResult.file_path);
      setProcessingStatus(res.message);
    } catch (err) {
      setProcessingStatus('Processing failed to start.');
    }
  };

  return (
    <div className="p-4 md:p-8 text-white max-w-6xl mx-auto min-h-screen bg-transparent">
      <div className="flex items-center gap-4 mb-8 md:mb-12 bg-slate-800/80 backdrop-blur-xl p-6 md:p-8 rounded-3xl border border-slate-700/50 shadow-2xl">
        <div className="bg-gradient-to-br from-blue-500 to-blue-700 p-4 rounded-2xl shadow-lg shadow-blue-600/30">
          <Video className="text-white w-8 h-8" />
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Footage Processing</h1>
          <p className="text-slate-400 text-sm md:text-base mt-1">Safely inject offline video files into the live AI inference engine.</p>
        </div>
      </div>

      <div className={`grid grid-cols-1 ${analysisResults ? 'xl:grid-cols-3' : 'lg:grid-cols-2'} gap-8 relative items-start`}>
        
        {/* Left Side: Upload & Configure */}
        <div className={`col-span-1 space-y-8 ${analysisResults ? 'xl:col-span-1' : ''}`}>
          {/* Step 1 */}
        <div className={`bg-slate-800/80 p-6 md:p-8 rounded-3xl border transition-all duration-500 shadow-xl ${uploadResult ? 'border-green-500/30 bg-green-900/5' : 'border-slate-700/50 hover:border-slate-600'}`}>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-4">
              <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-lg font-bold shadow-lg shadow-blue-500/30 border border-blue-400/20">1</span>
              Upload File
            </h2>
            {uploadResult && <CheckCircle className="w-8 h-8 text-green-500 animate-pulse drop-shadow-[0_0_10px_rgba(34,197,94,0.5)]" />}
          </div>
          
          <form onSubmit={handleUpload} className="space-y-6">
            <div className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer group ${uploadResult ? 'border-green-500/30 bg-green-500/5' : 'border-slate-600 hover:border-blue-500 bg-slate-900/50 hover:bg-slate-900/80 hover:shadow-[0_0_30px_rgba(59,130,246,0.1)]'}`}>
              <input 
                type="file" 
                accept="video/mp4,video/avi,video/mkv"
                onChange={(e) => setFile(e.target.files[0])}
                disabled={uploadResult}
                className="w-full text-slate-400 file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-blue-600 file:text-white hover:file:bg-blue-500 text-sm file:transition-all file:cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {!uploadResult && <p className="text-xs text-slate-500 mt-4 font-medium tracking-wide">ACCEPTS .MP4, .AVI, .MKV</p>}
            </div>
            
            <button 
              type="submit" 
              disabled={!file || uploading || uploadResult}
              className={`w-full p-4 rounded-xl font-bold text-lg flex justify-center items-center transition-all duration-300 ${
                uploadResult ? 'bg-green-600/20 text-green-400 border border-green-500/20' : 
                (!file || uploading ? 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-xl shadow-blue-500/25 hover:-translate-y-0.5')
              }`}
            >
              {uploadResult ? "File Securely Vaulted" : uploading ? <span className="animate-pulse flex items-center"><div className="w-5 h-5 border-2 border-slate-300 border-t-white rounded-full animate-spin mr-3"></div> Uploading...</span> : <><Upload className="w-6 h-6 mr-2" /> Upload Video</>}
            </button>
          </form>
        </div>

        {/* Fancy Arrow Connector for Desktop */}
        {!analysisResults && (
            <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-slate-950 p-2.5 rounded-full border border-slate-800 shadow-2xl">
              <ChevronRight className="w-8 h-8 text-slate-600" />
            </div>
        )}

        {/* Step 2 */}
        <div className={`bg-slate-800/80 p-6 md:p-8 rounded-3xl border transition-all duration-700 shadow-xl ${!uploadResult ? 'opacity-40 grayscale-[80%] pointer-events-none border-slate-800' : 'border-indigo-500/30 ring-1 ring-indigo-500/10 translate-y-0'}`}>
          <div className="flex items-center mb-8">
            <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-4">
              <span className={`flex items-center justify-center w-10 h-10 rounded-xl text-lg font-bold shadow-lg border ${uploadResult ? 'bg-gradient-to-br from-indigo-500 to-purple-600 border-indigo-400/20 shadow-indigo-500/30 text-white' : 'bg-slate-900 border-slate-700 text-slate-600'}`}>2</span>
              Initialize AI Engine
            </h2>
          </div>
          
          <div className="space-y-6">
            <button 
              onClick={handleProcess}
              disabled={!uploadResult || !selectedCameraId || processingStatus}
              className={`w-full p-6 rounded-2xl font-bold text-xl flex justify-center items-center transition-all duration-300 ${
                !uploadResult || !selectedCameraId || processingStatus ? 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800' : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-2xl shadow-indigo-500/25 hover:-translate-y-1'
              }`}
            >
              <ServerCog className={`w-8 h-8 mr-3 ${processingStatus ? 'animate-spin opacity-50' : ''}`} /> 
              {processingStatus ? 'Engine Active & Analyzing...' : 'Start Intelligence Inference'}
            </button>

            {processingStatus && (
              <div className="mt-6 p-5 bg-indigo-500/10 border border-indigo-500/30 rounded-xl shadow-inner">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-indigo-300 font-medium flex items-center gap-3">
                    {isProcessing && <div className="w-2 h-2 bg-indigo-400 rounded-full animate-ping"></div>}
                    {processingStatus}
                  </div>
                  <div className="text-indigo-200 text-sm font-bold">{progress}%</div>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-3 max-w-full overflow-hidden border border-slate-700">
                  <div 
                    className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-300 ease-out" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        </div>
        </div>

        {/* Right Side: Step 3 / Analytics Sidebar */}
        {analysisResults && (
          <div className="col-span-1 xl:col-span-2 bg-slate-800/80 p-6 md:p-8 rounded-3xl border border-indigo-500/30 shadow-[0_0_40px_rgba(79,70,229,0.15)] animate-enter flex flex-col h-full max-h-[800px]">
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-700/50">
              <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-4">
                <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 text-lg font-bold shadow-lg shadow-green-500/30 text-white border border-green-400/20">3</span>
                Analysis Data Matrix
              </h2>
              <div className="px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/30 rounded-lg flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" />
                <span className="text-sm font-bold text-indigo-300">{analysisResults.length} Events Detected</span>
              </div>
            </div>
            
            <div className="flex-1 overflow-x-auto overflow-y-auto custom-scrollbar -mx-2 px-2 pb-4">
               <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-700/50 bg-slate-900/50">
                      <th className="p-3 text-xs font-bold text-indigo-400 uppercase tracking-widest whitespace-nowrap w-24"><ScanLine className="w-4 h-4 inline mr-1"/> SNAPSHOT</th>
                      <th className="p-3 text-xs font-bold text-indigo-400 uppercase tracking-widest">VEHICLE ID & TYPE</th>
                      <th className="p-3 text-xs font-bold text-indigo-400 uppercase tracking-widest"><Hash className="w-4 h-4 inline mr-1"/> NUMBER PLATE</th>
                      <th className="p-3 text-xs font-bold text-indigo-400 uppercase tracking-widest">CONFIDENCE</th>
                      <th className="p-3 text-xs font-bold text-indigo-400 uppercase tracking-widest whitespace-nowrap"><Clock className="w-4 h-4 inline mr-1"/> TIMESTAMP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisResults.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="p-12 text-center text-slate-500 font-medium border-b border-slate-700/50">No definitive vehicle profiles were identified in this upload.</td>
                      </tr>
                    ) : analysisResults.map((item, idx) => (
                      <tr key={item.id || idx} onClick={() => setActiveRecord(item)} className="border-b border-slate-700/20 hover:bg-slate-800/80 transition-colors group cursor-pointer">
                        <td className="p-3">
                           <div className="w-20 h-14 bg-slate-950 rounded-lg border border-slate-700/50 overflow-hidden shadow-lg group-hover:border-indigo-500/80 group-hover:shadow-[0_0_15px_rgba(79,70,229,0.3)] transition-all">
                              <img src={getImageUrl(item.snapshot_path)} alt="Frame" className="w-full h-full object-cover bg-slate-900" onError={e => e.target.src=fallbackImage} />
                           </div>
                        </td>
                        <td className="p-3">
                           <div className="flex items-center gap-2 mb-1">
                             <div className="p-1.5 bg-slate-900 rounded-md border border-slate-700 text-indigo-400">
                               <Car className="w-4 h-4" />
                             </div>
                             <p className="font-bold text-slate-200 uppercase">{item.vehicle_type || 'VEHICLE'}</p>
                           </div>
                           <span className="text-[10px] text-slate-500 font-mono tracking-widest px-1">TRK-ID: {item.tracking_id}</span>
                        </td>
                        <td className="p-3">
                           {item.number_plate ? (
                             <div className="inline-block bg-[#ffea00] border-2 border-black rounded shadow-sm px-3 py-1">
                               <span className="font-mono text-black font-bold tracking-wider text-sm">{item.number_plate}</span>
                             </div>
                           ) : (
                             <span className="text-slate-600 font-mono text-xs italic">UNREADABLE</span>
                           )}
                        </td>
                        <td className="p-3">
                           <div className="flex items-center gap-2 mb-1">
                             <span className="text-xs font-bold font-mono text-green-400">{Math.round((item.plate_confidence || item.confidence || 0.8) * 100)}%</span>
                           </div>
                           <div className="w-24 h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                             <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400" style={{ width: `${Math.round((item.plate_confidence || item.confidence || 0.8) * 100)}%` }}></div>
                           </div>
                        </td>
                        <td className="p-3">
                           <p className="font-mono text-sm font-semibold text-slate-300">{new Date(item.last_seen || item.timestamp).toLocaleTimeString()}</p>
                           <p className="text-[10px] text-slate-500 font-bold uppercase">{new Date(item.last_seen || item.timestamp).toLocaleDateString()}</p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
               </table>
            </div>
          </div>
        )}
      </div>

      {/* Expanded Details Analytics Modal */}
      {activeRecord && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[100] flex justify-center items-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-4xl shadow-[0_0_100px_rgba(79,70,229,0.2)] animate-enter grid grid-cols-1 md:grid-cols-2 overflow-hidden relative">
            <button onClick={() => setActiveRecord(null)} className="absolute top-4 right-4 bg-slate-800/50 hover:bg-slate-700 p-2 rounded-full text-slate-300 transition-colors z-10">
               <X className="w-5 h-5" />
            </button>
            
            <div className="bg-slate-950 flex flex-col justify-center items-center relative border-b md:border-b-0 md:border-r border-slate-700/50 min-h-[300px]">
               <img src={getImageUrl(activeRecord.snapshot_path)} alt="Extraction" className="w-full h-full object-contain bg-slate-900" onError={e => e.target.src=fallbackImage} />
               <div className="absolute top-4 left-4 flex gap-2">
                 <span className="bg-indigo-600 font-bold px-3 py-1 rounded text-xs shadow-lg flex items-center">
                   <ScanLine className="w-3 h-3 mr-2" /> V-EXTRACT: {activeRecord.tracking_id}
                 </span>
               </div>
            </div>

            <div className="p-8 md:p-10 flex flex-col justify-center space-y-8">
               <div>
                  <h3 className="text-slate-400 font-semibold mb-1 flex items-center text-xs tracking-widest"><Search className="w-4 h-4 mr-2" /> RECOGNIZED NUMBER PLATE</h3>
                  {activeRecord.number_plate ? (
                    <div className="inline-block bg-[#ffea00] border-4 border-black text-black font-mono font-bold text-4xl px-6 py-3 rounded-lg shadow-xl shadow-yellow-500/10">
                      {activeRecord.number_plate}
                    </div>
                  ) : (
                    <div className="inline-block bg-slate-800 border-4 border-slate-700 text-slate-500 font-mono font-bold text-4xl px-6 py-3 rounded-lg">
                      UNREADABLE
                    </div>
                  )}
               </div>

               <div>
                 <h3 className="text-slate-400 font-semibold mb-3 flex items-center text-xs tracking-widest"><FileText className="w-4 h-4 mr-2" /> METADATA PROFILE</h3>
                 <div className="grid grid-cols-2 gap-4">
                   <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                     <p className="text-xs text-slate-500 mb-1">OBJECT CLASSIFICATION</p>
                     <p className="font-bold text-lg text-indigo-300 uppercase">{activeRecord.vehicle_type || 'VEHICLE'}</p>
                   </div>
                   <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                     <p className="text-xs text-slate-500 mb-1">AI CONFIDENCE</p>
                     <div className="flex items-center gap-3">
                       <p className="font-bold text-lg text-green-400">{Math.round((activeRecord.plate_confidence || activeRecord.confidence || 0.8) * 100)}%</p>
                       <div className="flex-1 h-2 bg-slate-900 rounded-full overflow-hidden">
                         <div className="h-full bg-green-500" style={{ width: `${Math.round((activeRecord.plate_confidence || activeRecord.confidence || 0.8) * 100)}%` }}></div>
                       </div>
                     </div>
                   </div>
                 </div>
               </div>

               <div>
                 <h3 className="text-slate-400 font-semibold mb-3 flex items-center text-xs tracking-widest"><Clock className="w-4 h-4 mr-2" /> EVENT TIMESTAMPS</h3>
                 <div className="flex items-center justify-between text-sm p-4 bg-slate-800/20 rounded-xl border border-slate-700/50 font-mono">
                   <span>LAST SIGHTED</span>
                   <span className="text-indigo-400 font-bold">{new Date(activeRecord.last_seen || activeRecord.timestamp).toLocaleString()}</span>
                 </div>
               </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
