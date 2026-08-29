import { BookOpen, Camera, Video, Bell, Upload, ServerCog } from 'lucide-react';

export default function HelpGuide() {
  return (
    <div className="p-4 md:p-8 text-slate-200 min-h-screen bg-transparent max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-blue-600/20 rounded-2xl border border-blue-500/30 shadow-lg shadow-blue-500/20">
          <BookOpen className="w-8 h-8 text-blue-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow-md">System Walkthrough</h1>
          <p className="text-slate-400 text-sm mt-1">Learn how to operate the AI Command Center modules step-by-step.</p>
        </div>
      </div>
      
      <div className="space-y-6 animate-enter">
        <div className="glass-card p-6 md:p-8 rounded-[2rem] relative overflow-hidden border border-blue-500/10 hover:border-blue-500/30 transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl pointer-events-none"></div>
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3 relative z-10">
            <span className="flex items-center justify-center w-10 h-10 rounded-2xl bg-blue-600/20 text-blue-400 text-lg font-bold border border-blue-500/30 shadow-lg shadow-blue-500/10">1</span>
            Configure Cameras
          </h2>
          <div className="flex gap-4 relative z-10">
            <div className="mt-1"><Camera className="text-slate-500 w-6 h-6" /></div>
            <div>
              <p className="text-slate-300 mb-2 font-medium">Before doing anything else, you must tell the system where the footage is coming from.</p>
              <ul className="list-disc pl-5 text-sm text-slate-400 space-y-2">
                <li>Navigate to <strong>Live Cameras</strong> in the sidebar.</li>
                <li>Add a new Virtual Camera Node with a logic name (e.g. "Main Gate") and an ID (e.g. "CAM-01").</li>
                <li>This virtual camera will now be available across the Neural Intelligence network.</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="glass-card p-6 md:p-8 rounded-[2rem] relative overflow-hidden border border-indigo-500/10 hover:border-indigo-500/30 transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none"></div>
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3 relative z-10">
            <span className="flex items-center justify-center w-10 h-10 rounded-2xl bg-indigo-600/20 text-indigo-400 text-lg font-bold border border-indigo-500/30 shadow-lg shadow-indigo-500/10">2</span>
            Process Footage
          </h2>
          <div className="flex gap-4 relative z-10">
            <div className="mt-1"><Video className="text-slate-500 w-6 h-6" /></div>
            <div>
              <p className="text-slate-300 mb-2 font-medium">Inject offline video files to run through our AI engine.</p>
              <ul className="list-disc pl-5 text-sm text-slate-400 space-y-2">
                <li>Go to <strong>Video Inference</strong>.</li>
                <li><span className="text-indigo-400 bg-indigo-400/10 px-2 py-0.5 rounded font-mono font-bold">Step 1</span>: Select a .MP4 file and click the blue <strong>Upload Video</strong> button. Wait for the green success box.</li>
                <li><span className="text-indigo-400 bg-indigo-400/10 px-2 py-0.5 rounded font-mono font-bold">Step 2</span>: Select the camera you created earlier from the dropdown menu.</li>
                <li>Click <strong>Start Inference Engine</strong> to begin tracking objects using YOLOv11 and ByteTrack backend processing.</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="glass-card p-6 md:p-8 rounded-[2rem] relative overflow-hidden border border-purple-500/10 hover:border-purple-500/30 transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl pointer-events-none"></div>
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3 relative z-10">
            <span className="flex items-center justify-center w-10 h-10 rounded-2xl bg-purple-600/20 text-purple-400 text-lg font-bold border border-purple-500/30 shadow-lg shadow-purple-500/10">3</span>
            Investigations & Analytics
          </h2>
          <div className="flex gap-4 relative z-10">
            <div className="mt-1"><ServerCog className="text-slate-500 w-6 h-6" /></div>
            <div>
              <p className="text-slate-300 mb-2 font-medium">Review processed findings and manage active incidents.</p>
              <ul className="list-disc pl-5 text-sm text-slate-400 space-y-2">
                <li><strong>Dashboard Overview</strong> will automatically compile statistics of detected traffic patterns and show critical rules violations.</li>
                <li>Go to <strong>Investigation</strong> to instantly query the MySQL database for full or partial vehicle Number Plates caught by EasyOCR.</li>
                <li>Critical alerts (like tracking stationary items) will appear as red notifications across the screen dynamically using WebSockets.</li>
              </ul>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
