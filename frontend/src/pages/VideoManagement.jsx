import { useState, useEffect } from 'react';
import { uploadVideo, startProcessing } from '../services/videoService';
import { getCameras } from '../services/cameraService';
import { Video, Upload, ServerCog, CheckCircle, ChevronRight } from 'lucide-react';

export default function VideoManagement() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [processingStatus, setProcessingStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

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
    } catch (err) {
      console.error(err);
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 relative">
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
        <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-slate-950 p-2.5 rounded-full border border-slate-800 shadow-2xl">
          <ChevronRight className="w-8 h-8 text-slate-600" />
        </div>

        {/* Step 2 */}
        <div className={`bg-slate-800/80 p-6 md:p-8 rounded-3xl border transition-all duration-700 shadow-xl ${!uploadResult ? 'opacity-40 grayscale-[80%] pointer-events-none border-slate-800' : 'border-indigo-500/30 ring-1 ring-indigo-500/10 translate-y-0'}`}>
          <div className="flex items-center mb-8">
            <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-4">
              <span className={`flex items-center justify-center w-10 h-10 rounded-xl text-lg font-bold shadow-lg border ${uploadResult ? 'bg-gradient-to-br from-indigo-500 to-purple-600 border-indigo-400/20 shadow-indigo-500/30 text-white' : 'bg-slate-900 border-slate-700 text-slate-600'}`}>2</span>
              Configure AI Rules
            </h2>
          </div>
          
          <div className="space-y-6">
            <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-700/50">
              <label className="block text-sm font-semibold text-indigo-300/80 mb-3 tracking-wide">ATTACH TO CAMERA ID</label>
              <select 
                value={selectedCameraId}
                onChange={(e) => setSelectedCameraId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 rounded-xl p-4 text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-medium appearance-none shadow-inner"
              >
                <option value="">-- View Camera List --</option>
                {cameras.map(cam => (
                  <option key={cam.id} value={cam.id}>{cam.camera_name} ({cam.camera_code})</option>
                ))}
              </select>
            </div>

            <button 
              onClick={handleProcess}
              disabled={!uploadResult || !selectedCameraId || processingStatus}
              className={`w-full p-4 rounded-xl font-bold text-lg flex justify-center items-center transition-all duration-300 ${
                !uploadResult || !selectedCameraId || processingStatus ? 'bg-slate-900 text-slate-600 cursor-not-allowed border border-slate-800' : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-2xl shadow-indigo-500/25 hover:-translate-y-0.5'
              }`}
            >
              <ServerCog className={`w-6 h-6 mr-3 ${processingStatus ? 'animate-spin opacity-50' : ''}`} /> 
              {processingStatus ? 'Engine Active & Analyzing...' : 'Start Inference Engine'}
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
    </div>
  );
}
