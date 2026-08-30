import { useState, useEffect } from 'react';
import { searchVehicles } from '../services/dataService';
import { Database, Search, FileText, ScanLine, Clock, X, Hash, Car, Filter, RefreshCw } from 'lucide-react';

const getImageUrl = (path) => {
  if (!path) return 'https://via.placeholder.com/150?text=No+Photo';
  if (path.startsWith('http')) return path;
  let cleanPath = path.replace(/\\/g, '/');
  if (cleanPath.startsWith('uploads/')) {
    cleanPath = '/static/' + cleanPath.substring(8);
  } else if (!cleanPath.startsWith('/')) {
    cleanPath = '/' + cleanPath;
  }
  return `http://localhost:8000${cleanPath}`;
};

export default function ViewRecords() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeRecord, setActiveRecord] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchRecords = async () => {
    setLoading(true);
    try {
      // Without params, it returns the global limit of the latest records.
      const data = await searchVehicles({});
      setRecords(data);
    } catch (err) {
      console.error("Failed to load records", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const filteredRecords = records.filter(item => 
    (item.number_plate && item.number_plate.includes(searchTerm.toUpperCase())) ||
    (item.vehicle_type && item.vehicle_type.toUpperCase().includes(searchTerm.toUpperCase())) ||
    (item.tracking_id && item.tracking_id.toString() === searchTerm)
  );

  return (
    <div className="p-4 md:p-8 text-white min-h-screen bg-transparent">
      
      {/* Header */}
      <div className="bg-slate-800/80 backdrop-blur-xl p-6 md:p-8 rounded-3xl border border-slate-700/50 shadow-2xl mb-8 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
         <div className="flex items-center gap-5">
           <div className="p-4 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-2xl shadow-[0_0_20px_rgba(59,130,246,0.3)]">
             <Database className="w-8 h-8 text-white" />
           </div>
           <div>
             <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-1">GLOBAL RECORDS LEDGER</h1>
             <p className="text-slate-400 text-sm font-mono tracking-widest">{records.length} UNIFIED INTELLIGENCE LOGS</p>
           </div>
         </div>
         
         <div className="flex flex-col sm:flex-row w-full lg:w-auto gap-4">
           <div className="relative flex-1 sm:w-64">
             <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
               <Filter className="h-4 w-4 text-slate-500" />
             </div>
             <input
               type="text"
               placeholder="Filter by plate, ID..."
               value={searchTerm}
               onChange={(e) => setSearchTerm(e.target.value)}
               className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-slate-200 focus:outline-none focus:border-indigo-500 shadow-inner font-mono text-sm uppercase"
             />
           </div>
           
           <button 
             onClick={fetchRecords} 
             disabled={loading}
             className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-bold flex items-center justify-center transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)] disabled:opacity-50"
           >
             <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
             Refresh
           </button>
         </div>
      </div>

      <div className="bg-slate-800/80 rounded-3xl border border-slate-700/50 shadow-2xl animate-enter">
          <div className="overflow-x-auto w-full rounded-3xl p-1">
             <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/80 border-b border-slate-700">
                    <th className="p-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap"><ScanLine className="w-4 h-4 inline mr-2"/> EVIDENCE FRAME</th>
                    <th className="p-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap"><Car className="w-4 h-4 inline mr-2"/> OBJECT CLASS & ID</th>
                    <th className="p-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest"><Hash className="w-4 h-4 inline mr-1"/> SYSTEM RECOGNIZED PLATE</th>
                    <th className="p-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest w-48">MATCH CONFIDENCE</th>
                    <th className="p-5 text-[11px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap"><Clock className="w-4 h-4 inline mr-2"/> TIME & CAMERA NODE</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan="5" className="p-16 text-center text-slate-500 font-bold uppercase tracking-widest">
                         <RefreshCw className="w-8 h-8 mx-auto mb-4 animate-spin opacity-50" />
                         Syncing Global Database...
                      </td>
                    </tr>
                  ) : filteredRecords.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="p-16 text-center text-slate-500 font-bold uppercase tracking-widest">
                         No intelligence records found matching criteria
                      </td>
                    </tr>
                  ) : filteredRecords.map((item, idx) => (
                    <tr key={item.id || idx} onClick={() => setActiveRecord(item)} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors group cursor-pointer">
                      <td className="p-4">
                         <div className="w-28 h-20 bg-slate-950 rounded-xl border border-slate-700 overflow-hidden shadow-lg group-hover:border-indigo-500/80 transition-all">
                            <img src={getImageUrl(item.snapshot_path)} alt="Frame" className="w-full h-full object-cover" onError={e => e.target.src='https://via.placeholder.com/200?text=No+Photo'} />
                         </div>
                      </td>
                      <td className="p-4">
                         <div className="flex items-center gap-3 mb-2">
                           <div className="p-2 bg-slate-900 rounded-lg border border-slate-700 text-indigo-400">
                             <Car className="w-4 h-4" />
                           </div>
                           <p className="font-bold text-slate-200 uppercase tracking-wider">{item.vehicle_type || 'VEHICLE'}</p>
                         </div>
                         <span className="bg-slate-900 text-slate-400 px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border border-slate-800">TRK-{item.tracking_id}</span>
                      </td>
                      <td className="p-4">
                         {item.number_plate ? (
                           <div className="inline-block bg-[#ffea00] border-2 border-black rounded shadow-[0_0_10px_rgba(255,234,0,0.15)] px-4 py-1.5">
                             <span className="font-mono text-black font-extrabold tracking-widest text-lg">{item.number_plate}</span>
                           </div>
                         ) : (
                           <span className="text-slate-500 font-mono text-xs italic bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">UNREADABLE</span>
                         )}
                      </td>
                      <td className="p-4">
                         <div className="flex items-center gap-3 mb-1.5">
                           <span className="text-sm font-bold font-mono text-green-400">{Math.round((item.plate_confidence || item.confidence || 0.8) * 100)}%</span>
                           <span className="text-[10px] text-slate-500 uppercase tracking-widest">Accuracy</span>
                         </div>
                         <div className="w-32 h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800 shadow-inner">
                           <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400" style={{ width: `${Math.round((item.plate_confidence || item.confidence || 0.8) * 100)}%` }}></div>
                         </div>
                      </td>
                      <td className="p-4">
                         <p className="font-mono text-[15px] font-bold text-slate-200 mb-1">{new Date(item.last_seen || item.timestamp).toLocaleTimeString()}</p>
                         <div className="flex items-center gap-2 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                           <span>{new Date(item.last_seen || item.timestamp).toLocaleDateString()}</span>
                           <span className="text-slate-600">•</span>
                           <span className="text-blue-400">CAM {item.camera_id}</span>
                         </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
             </table>
          </div>
      </div>

      {/* Expanded Modal (Deep Investigation) */}
      {activeRecord && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[100] flex justify-center items-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-4xl shadow-[0_0_150px_rgba(79,70,229,0.3)] animate-enter grid grid-cols-1 md:grid-cols-2 overflow-hidden relative">
            <button onClick={() => setActiveRecord(null)} className="absolute top-4 right-4 bg-slate-800/80 hover:bg-slate-700 p-2.5 rounded-full text-white transition-colors z-10 shadow-lg">
               <X className="w-5 h-5" />
            </button>
            
            <div className="bg-slate-950 flex flex-col justify-center items-center relative border-b md:border-b-0 md:border-r border-slate-700/50 min-h-[350px]">
               <img src={getImageUrl(activeRecord.snapshot_path)} alt="Extraction" className="w-full h-full object-contain" onError={e => e.target.src='https://via.placeholder.com/600'} />
               <div className="absolute top-4 left-4 flex gap-2">
                 <span className="bg-indigo-600 text-white font-bold px-3 py-1.5 rounded-lg text-xs shadow-lg flex items-center tracking-widest border border-indigo-400/30">
                   <ScanLine className="w-3.5 h-3.5 mr-2" /> CAPTURE TRK-{activeRecord.tracking_id}
                 </span>
               </div>
            </div>

            <div className="p-8 md:p-10 flex flex-col justify-center space-y-8 bg-slate-900">
               <div>
                  <h3 className="text-slate-400 font-semibold mb-2 flex items-center text-xs tracking-widest"><Search className="w-4 h-4 mr-2" /> RECOGNIZED NUMBER PLATE</h3>
                  {activeRecord.number_plate ? (
                    <div className="inline-block bg-[#ffea00] border-4 border-black text-black font-mono font-bold text-5xl px-8 py-4 rounded-xl shadow-2xl shadow-yellow-500/10 tracking-wider">
                      {activeRecord.number_plate}
                    </div>
                  ) : (
                    <div className="inline-block bg-slate-800 border-4 border-slate-700 text-slate-500 font-mono font-bold text-4xl px-6 py-3 rounded-xl">
                      UNREADABLE
                    </div>
                  )}
               </div>

               <div>
                 <h3 className="text-slate-400 font-semibold mb-3 flex items-center text-xs tracking-widest"><FileText className="w-4 h-4 mr-2" /> METADATA PROFILE</h3>
                 <div className="grid grid-cols-2 gap-4">
                   <div className="bg-slate-800/60 p-5 rounded-2xl border border-slate-700/70 shadow-inner">
                     <p className="text-[10px] text-slate-500 mb-1.5 font-bold tracking-widest uppercase">CLASSIFICATION</p>
                     <p className="font-bold text-xl text-indigo-300 uppercase">{activeRecord.vehicle_type || 'VEHICLE'}</p>
                   </div>
                   <div className="bg-slate-800/60 p-5 rounded-2xl border border-slate-700/70 shadow-inner">
                     <p className="text-[10px] text-slate-500 mb-2 font-bold tracking-widest uppercase">AI CONFIDENCE</p>
                     <div className="flex items-center gap-3">
                       <p className="font-bold text-xl text-green-400">{Math.round((activeRecord.plate_confidence || activeRecord.confidence || 0.8) * 100)}%</p>
                       <div className="flex-1 h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
                         <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400 shadow-[0_0_10px_rgba(34,197,94,0.5)]" style={{ width: `${Math.round((activeRecord.plate_confidence || activeRecord.confidence || 0.8) * 100)}%` }}></div>
                       </div>
                     </div>
                   </div>
                 </div>
               </div>

               <div>
                 <h3 className="text-slate-400 font-semibold mb-3 flex items-center text-[10px] tracking-widest font-bold uppercase"><Clock className="w-4 h-4 mr-2" /> EVENT METRICS</h3>
                 <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-2xl border border-slate-700/50 font-mono shadow-inner">
                   <div className="flex flex-col">
                     <span className="text-[10px] text-slate-500 mb-1">NODE ATTACHMENT</span>
                     <span className="text-slate-300 font-bold">CAM_{activeRecord.camera_id}</span>
                   </div>
                   <div className="flex flex-col items-end">
                     <span className="text-[10px] text-slate-500 mb-1">LAST SIGHTED (UTC)</span>
                     <span className="text-indigo-400 font-bold text-lg">{new Date(activeRecord.last_seen || activeRecord.timestamp).toLocaleTimeString()}</span>
                   </div>
                 </div>
               </div>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}
