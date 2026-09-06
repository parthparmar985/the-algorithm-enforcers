import { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import { AlertTriangle, CheckCircle, Clock, MapPin, RotateCcw, Search } from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import InvestigationEvidence from '../components/InvestigationEvidence';
import api from '../services/api';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const selectedIcon = L.divIcon({
  className: '',
  html: '<div style="width:24px;height:24px;border-radius:50%;background:#ef4444;border:4px solid white;box-shadow:0 0 14px #ef4444"></div>',
  iconSize: [24, 24], iconAnchor: [12, 12],
});
const emptyFilters = { registration_number: '', camera_id: '', location: '', vehicle_type: '', start_time: '', end_time: '' };
const fieldClass = 'w-full bg-slate-900/80 border border-slate-600 rounded-xl px-3 py-3 text-white focus:outline-none focus:border-indigo-500';
const buttonClass = 'px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed font-semibold';

function utcToLocalInput(value) {
  if (!value) return '';
  const date = new Date(`${value}${/[zZ]|[+-]\d\d:\d\d$/.test(value) ? '' : 'Z'}`);
  if (Number.isNaN(date.getTime())) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function imageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  let clean = path.replace(/\\/g, '/');
  if (clean.startsWith('uploads/')) clean = `/static/${clean.slice(8)}`;
  else if (!clean.startsWith('/')) clean = `/${clean}`;
  return `http://localhost:8000${clean}`;
}

function MapFocus({ event }) {
  const map = useMap();
  useEffect(() => {
    if (event?.latitude != null && event?.longitude != null) map.flyTo([event.latitude, event.longitude], Math.max(map.getZoom(), 15));
  }, [event, map]);
  return null;
}

export default function Investigation() {
  const [filters, setFilters] = useState(emptyFilters);
  const [cameras, setCameras] = useState([]);
  const [results, setResults] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [activePlate, setActivePlate] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [naturalQuery, setNaturalQuery] = useState('');
  const [naturalResponse, setNaturalResponse] = useState(null);
  const evidencePanel = useRef(null);

  useEffect(() => {
    api.get('/cameras/').then(response => setCameras(response.data)).catch(() => setError('Camera filters could not be loaded.'));
  }, []);

  const updateFilter = event => setFilters(current => ({ ...current, [event.target.name]: event.target.value }));

  async function selectPlate(plate) {
    setLoading(true); setError('');
    try {
      const { data } = await api.get(`/search/trace/${encodeURIComponent(plate)}`);
      setActivePlate(plate); setTimeline(data); setSelectedEvent(data[0] || null);
      if (!data.length) setError('No chronological sightings are available for that plate.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to load the vehicle timeline.');
      setTimeline([]); setActivePlate('');
    } finally { setLoading(false); }
  }

  async function search(event) {
    event.preventDefault();
    if (filters.start_time && filters.end_time && filters.start_time > filters.end_time) {
      setError('From date/time must be before To date/time.'); return;
    }
    setLoading(true); setSearched(true); setError(''); setTimeline([]); setActivePlate('');
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''));
      for (const key of ['start_time', 'end_time']) {
        if (params[key]) params[key] = new Date(params[key]).toISOString();
      }
      const { data } = await api.get('/search/investigations', { params });
      setResults(data);
      const plates = [...new Set(data.map(row => row.registration_number).filter(Boolean))];
      if (plates.length === 1) await selectPlate(plates[0]);
    } catch (requestError) {
      setResults([]);
      setError(requestError.response?.data?.detail || 'Investigation search failed. Please retry.');
    } finally { setLoading(false); }
  }

  async function naturalSearch(event) {
    event.preventDefault();
    if (!naturalQuery.trim()) return;
    setLoading(true); setSearched(true); setError(''); setTimeline([]); setActivePlate('');
    try {
      const { data } = await api.post('/search/natural', { query: naturalQuery });
      setNaturalResponse(data);
      const parsed = data.parsed_filters || {};
      setFilters({
        registration_number: parsed.registration_number || '',
        camera_id: parsed.camera_id == null ? '' : String(parsed.camera_id),
        location: parsed.location || '',
        vehicle_type: parsed.vehicle_type || '',
        start_time: utcToLocalInput(parsed.start_time),
        end_time: utcToLocalInput(parsed.end_time),
      });
      setResults(data.results || []);
      const plates = [...new Set((data.results || []).map(row => row.registration_number).filter(Boolean))];
      if (plates.length === 1) await selectPlate(plates[0]);
    } catch (requestError) {
      setNaturalResponse(null); setResults([]);
      setError(requestError.response?.data?.detail || 'Natural-language search failed. Please retry.');
    } finally { setLoading(false); }
  }

  function clearNatural() {
    setNaturalQuery(''); setNaturalResponse(null);
  }

  function chooseCamera(camera) {
    setFilters(current => ({ ...current, camera_id: String(camera.id), location: camera.location || '' }));
    setNaturalResponse(current => current ? {
      ...current,
      status: 'CAMERA_SELECTED',
      matches: [],
      interpretation: `Camera selected: ${camera.camera_name} (${camera.camera_code}). Review the structured filters, then search.`,
      parsed_filters: { ...current.parsed_filters, camera_id: camera.id, camera_name: camera.camera_name, location: camera.location || null },
    } : current);
  }

  function reset() {
    setFilters(emptyFilters); setResults([]); setTimeline([]); setActivePlate(''); setSelectedEvent(null); setSearched(false); setError(''); setNaturalQuery(''); setNaturalResponse(null);
  }

  const positions = timeline.filter(row => row.latitude != null && row.longitude != null).map(row => [row.latitude, row.longitude]);
  const mapCenter = positions[0] || [23.0225, 72.5714];
  const resultPlates = useMemo(() => [...new Set(results.map(row => row.registration_number).filter(Boolean))], [results]);

  return <div className="p-4 md:p-8 text-white max-w-[1400px] mx-auto min-h-screen">
    <section className="bg-slate-800/80 backdrop-blur-xl p-6 md:p-8 rounded-3xl border border-slate-700/50 shadow-2xl mb-8">
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight mb-2">AI VEHICLE INVESTIGATION</h1>
        <p className="text-slate-400 text-sm">Search stored vehicle sightings, then open a plate’s chronological route and evidence.</p>
      </div>
      <form onSubmit={naturalSearch} className="mb-6 p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30">
        <label htmlFor="natural-investigation-query" className="block font-semibold text-indigo-100 mb-2">Ask in plain language</label>
        <div className="flex flex-col md:flex-row gap-3">
          <input id="natural-investigation-query" aria-label="Natural-language investigation search" value={naturalQuery} onChange={event => setNaturalQuery(event.target.value)} maxLength={500} placeholder={'Search: "Find GJ01AB1234 near Gate 2 in the last hour"'} className={`${fieldClass} flex-1`} />
          <button type="submit" disabled={loading || !naturalQuery.trim()} className={`${buttonClass} flex items-center justify-center gap-2`}><Search className="w-4 h-4" />{loading ? 'Interpreting...' : 'Interpret and search'}</button>
          <button type="button" disabled={loading || (!naturalQuery && !naturalResponse)} onClick={clearNatural} className={`${buttonClass} bg-slate-700 hover:bg-slate-600`}>Clear</button>
        </div>
        <p className="text-xs text-slate-400 mt-2">Times entered in plain language are interpreted in Asia/Kolkata and queried against UTC records.</p>
      </form>

      {naturalResponse && <div aria-live="polite" className="mb-6 p-4 rounded-2xl bg-slate-900/70 border border-slate-700">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="font-bold text-slate-100">Understood as</h2>
          <span className={`text-xs px-2 py-1 rounded ${naturalResponse.status === 'AMBIGUOUS' ? 'bg-amber-500/20 text-amber-200' : naturalResponse.status === 'UNSUPPORTED' ? 'bg-red-500/20 text-red-200' : 'bg-emerald-500/20 text-emerald-200'}`}>{naturalResponse.status}</span>
        </div>
        <p className="text-sm text-slate-300 mt-2">{naturalResponse.interpretation}</p>
        <div className="flex flex-wrap gap-2 mt-3">
          {Object.entries(naturalResponse.parsed_filters || {}).filter(([key, value]) => value != null && key !== 'camera_name').map(([key, value]) => <span key={key} className="text-xs bg-indigo-500/15 border border-indigo-500/30 text-indigo-100 px-2 py-1 rounded">{key.replaceAll('_', ' ')}: {String(value)}</span>)}
        </div>
        {(naturalResponse.warnings || []).map(warning => <p key={warning} className="text-sm text-amber-300 mt-2">{warning}</p>)}
        {(naturalResponse.matches || []).length > 0 && <div className="mt-3"><p className="text-sm text-slate-300 mb-2">Choose the intended camera:</p><div className="flex flex-wrap gap-2">{naturalResponse.matches.map(camera => <button type="button" key={camera.id} onClick={() => chooseCamera(camera)} className="px-3 py-2 text-sm rounded-lg bg-amber-600 hover:bg-amber-500">{camera.camera_name} ({camera.camera_code}) - {camera.location}</button>)}</div></div>}
        {naturalResponse.status === 'PARSED' && naturalResponse.result_count === 0 && <p className="mt-3 text-slate-300">No detections matched the interpreted filters.</p>}
      </div>}

      <h2 className="font-bold text-slate-200 mb-3">Structured filters</h2>
      <form onSubmit={search} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <label className="text-sm text-slate-300">Plate
          <input aria-label="Plate" name="registration_number" value={filters.registration_number} onChange={event => setFilters(current => ({ ...current, registration_number: event.target.value.toUpperCase() }))} placeholder="GJ 01 AB 1234" className={`${fieldClass} mt-1 font-mono`} />
        </label>
        <label className="text-sm text-slate-300">Camera
          <select aria-label="Camera" name="camera_id" value={filters.camera_id} onChange={updateFilter} className={`${fieldClass} mt-1`}><option value="">All cameras</option>{cameras.map(camera => <option value={camera.id} key={camera.id}>{camera.camera_name} ({camera.camera_code})</option>)}</select>
        </label>
        <label className="text-sm text-slate-300">Location
          <input aria-label="Location" name="location" value={filters.location} onChange={updateFilter} placeholder="Ahmedabad" className={`${fieldClass} mt-1`} />
        </label>
        <label className="text-sm text-slate-300">Vehicle type
          <select aria-label="Vehicle type" name="vehicle_type" value={filters.vehicle_type} onChange={updateFilter} className={`${fieldClass} mt-1`}><option value="">All types</option>{['car', 'motorcycle', 'bus', 'truck'].map(type => <option value={type} key={type}>{type[0].toUpperCase() + type.slice(1)}</option>)}</select>
        </label>
        <label className="text-sm text-slate-300">From date/time
          <input aria-label="From date/time" type="datetime-local" name="start_time" value={filters.start_time} onChange={updateFilter} className={`${fieldClass} mt-1`} />
        </label>
        <label className="text-sm text-slate-300">To date/time
          <input aria-label="To date/time" type="datetime-local" name="end_time" value={filters.end_time} onChange={updateFilter} className={`${fieldClass} mt-1`} />
        </label>
        <div className="lg:col-span-3 flex gap-3 flex-wrap">
          <button type="submit" disabled={loading} className={`${buttonClass} flex items-center gap-2`}><Search className="w-4 h-4" />{loading ? 'Searching…' : 'Search'}</button>
          <button type="button" disabled={loading} onClick={reset} className={`${buttonClass} bg-slate-700 hover:bg-slate-600 flex items-center gap-2`}><RotateCcw className="w-4 h-4" />Reset filters</button>
        </div>
      </form>
    </section>

    {error && <p role="alert" className="p-4 mb-6 rounded-xl bg-red-900/20 border border-red-500/40 text-red-200">{error}</p>}
    {!searched && <div className="h-52 flex flex-col items-center justify-center text-slate-500 border-2 border-slate-700/50 border-dashed rounded-3xl"><Search className="w-12 h-12 mb-3" /><p>Choose any combination of filters to search stored sightings.</p></div>}
    {searched && !loading && !results.length && !error && <div className="p-8 text-center bg-slate-800/50 border border-slate-700 rounded-3xl"><AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-3" /><h2 className="font-bold">NO MATCHING SIGHTINGS</h2><p className="text-slate-400 mt-2">Adjust or reset the filters and try again.</p></div>}

    {results.length > 0 && <section className="bg-slate-800/80 p-6 rounded-3xl border border-slate-700 mb-8">
      <div className="flex justify-between gap-4 flex-wrap mb-4"><h2 className="text-xl font-bold">Search Results ({results.length})</h2><span className="text-sm text-slate-400">{resultPlates.length} plate{resultPlates.length === 1 ? '' : 's'}</span></div>
      <div className="max-h-72 overflow-y-auto space-y-2">
        {results.map(row => <button type="button" key={row.id} onClick={() => selectPlate(row.registration_number)} className="w-full text-left bg-slate-900 hover:bg-slate-700 p-4 rounded-xl flex justify-between gap-4 flex-wrap">
          <span><strong className="font-mono text-indigo-300">{row.registration_number || 'No plate'}</strong> · {row.vehicle_type} · {row.camera_name} · {row.location || 'Unknown location'}</span>
          <span className="text-slate-400">{new Date(`${row.timestamp}Z`).toLocaleString()} · Open timeline</span>
        </button>)}
      </div>
    </section>}

    {activePlate && timeline.length > 0 && <>
      <InvestigationEvidence key={activePlate} ref={evidencePanel} plate={activePlate} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <section className="lg:col-span-2 bg-slate-800/80 rounded-3xl border border-slate-700 overflow-hidden h-[620px] flex flex-col">
          <header className="p-5 flex justify-between border-b border-slate-700"><h2 className="font-bold flex items-center"><MapPin className="w-5 h-5 mr-2 text-indigo-400" />GIS Route</h2><span className="font-mono text-indigo-300">{activePlate}</span></header>
          <div className="flex-1 bg-slate-900">
            <MapContainer key={activePlate} center={mapCenter} zoom={13} style={{ height: '100%', width: '100%', zIndex: 10 }}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution="&copy; OpenStreetMap contributors" />
              <MapFocus event={selectedEvent} />
              {positions.length > 1 && <Polyline positions={positions} color="#6366f1" weight={4} dashArray="10, 10" />}
              {timeline.map((row, index) => row.latitude != null && row.longitude != null && <Marker key={row.id} position={[row.latitude, row.longitude]} icon={selectedEvent?.id === row.id ? selectedIcon : new L.Icon.Default()} eventHandlers={{ click: () => setSelectedEvent(row) }}>
                <Popup><div className="text-slate-800"><strong>{index + 1}. {row.camera_name}</strong><p>{row.location}</p><p>{new Date(`${row.timestamp}Z`).toLocaleString()}</p><p>{row.registration_number}</p></div></Popup>
              </Marker>)}
            </MapContainer>
          </div>
        </section>

        <section className="bg-slate-800/80 rounded-3xl border border-slate-700 h-[620px] flex flex-col">
          <header className="p-5 border-b border-slate-700"><h2 className="font-bold flex items-center"><Clock className="w-5 h-5 mr-2 text-indigo-400" />Vehicle Timeline</h2></header>
          <div className="p-5 overflow-y-auto flex-1 space-y-5">
            {timeline.map((row, index) => <article key={row.id} className="relative pl-7">
              {index < timeline.length - 1 && <div className="absolute left-2.5 top-6 h-full border-l-2 border-slate-600" />}
              <button type="button" onClick={() => setSelectedEvent(row)} className={`relative w-full text-left p-4 rounded-xl border ${selectedEvent?.id === row.id ? 'border-indigo-400 bg-indigo-900/20' : row.transition_status === 'ANOMALOUS TRANSITION' ? 'border-red-500/40 bg-red-900/10' : 'border-slate-700 bg-slate-900/60'}`}>
                <span className="absolute -left-7 top-4 w-5 h-5 rounded-full bg-indigo-500 border-4 border-slate-800" />
                <div className="flex justify-between gap-2"><strong>{new Date(`${row.timestamp}Z`).toLocaleTimeString()}</strong><span className="text-xs">{row.camera_code}</span></div>
                <p className="text-sm mt-1">{row.camera_name} · {row.location || 'Unknown location'}</p>
                <p className="font-mono text-indigo-300 mt-2">{row.registration_number} · {row.plate_confidence != null ? `${Math.round(row.plate_confidence * 100)}% plate confidence` : 'Confidence unavailable'}</p>
                {row.detection_confidence != null && <p className="text-xs text-slate-400">Object detection: {Math.round(row.detection_confidence * 100)}%</p>}
                {row.snapshot_path && <img src={imageUrl(row.snapshot_path)} alt={`${row.registration_number} at ${row.camera_name}`} className="mt-3 h-24 w-full object-cover rounded-lg" onError={event => { event.currentTarget.style.display = 'none'; }} />}
                {row.transition_status !== 'STARTPOINT' && <p className={`mt-3 text-xs flex items-center gap-1 ${row.transition_status === 'ANOMALOUS TRANSITION' ? 'text-red-300' : 'text-blue-300'}`}>{row.transition_status === 'ANOMALOUS TRANSITION' ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}{row.distance_km} km · {row.time_diff_mins} min · {row.calculated_speed_kmh == null ? 'Speed unavailable' : `${row.calculated_speed_kmh} km/h`}</p>}
                {row.alerts.map(alert => <p key={alert.id} className="mt-2 p-2 text-xs rounded bg-red-500/20 text-red-200">Alert: {alert.severity} · {alert.type}</p>)}
              </button>
              <button disabled={loading} className="mt-2 px-3 py-2 rounded-lg bg-indigo-600 text-sm disabled:opacity-40" onClick={() => evidencePanel.current?.add({ evidence_type: 'PLATE_DETECTION', vehicle_id: row.vehicle_id })}>+ Add timeline event to Evidence</button>
            </article>)}
          </div>
        </section>
      </div>
    </>}
  </div>;
}
