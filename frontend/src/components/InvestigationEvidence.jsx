import { forwardRef, useEffect, useImperativeHandle, useState } from 'react';
import api from '../services/api';

const button = 'px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm';
const time = value => value ? new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString() : 'Unavailable';

export default forwardRef(function InvestigationEvidence({ plate }, ref) {
  const [reference, setReference] = useState(null);
  const [context, setContext] = useState(null);
  const [basket, setBasket] = useState([]);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [preview, setPreview] = useState(null);
  const [description, setDescription] = useState('');

  useEffect(() => {
    let active = true;
    async function load() {
      setBusy(true);
      try {
        const { data: investigation } = await api.post('/evidence/investigations', { vehicle_plate: plate });
        const [summary, items] = await Promise.all([
          api.get(`/evidence/investigations/${investigation.id}`),
          api.get('/evidence', { params: { investigation_id: investigation.id } }),
        ]);
        if (active) {
          setReference(investigation.id); setContext(summary.data); setBasket(items.data);
          setSelected(items.data.map(e => e.id));
        }
      } catch (error) { if (active) setMessage(error.response?.data?.detail || 'Could not load investigation evidence. Search again to retry.'); }
      finally { if (active) setBusy(false); }
    }
    load();
    return () => { active = false; };
  }, [plate]);

  useEffect(() => () => { if (preview?.url) URL.revokeObjectURL(preview.url); }, [preview]);

  async function run(action) {
    if (busy) return;
    setBusy(true); setMessage('');
    try { await action(); }
    catch (error) {
      let data = error.response?.data;
      if (data instanceof Blob) { try { data = JSON.parse(await data.text()); } catch { data = null; } }
      setMessage(typeof data?.detail === 'string' ? data.detail : 'Request failed. Please retry.');
    } finally { setBusy(false); }
  }

  async function add(source) {
    if (!reference) { setMessage('Wait for the investigation to load before selecting evidence.'); return; }
    await run(async () => {
      const { data } = await api.post('/evidence', { investigation_id: reference, description, ...source });
      setBasket(items => items.some(e => e.id === data.id) ? items : [...items, data]);
      setSelected(ids => [...new Set([...ids, data.id])]);
      setMessage(`Evidence #${data.id} saved. Duplicate selections appear once.`);
    });
  }
  useImperativeHandle(ref, () => ({ add }));

  async function exportFile(format) {
    if (!selected.length) { setMessage('Select at least one evidence item.'); return; }
    await run(async () => {
      const { data } = await api.post('/evidence/export', { investigation_id: reference, evidence_ids: selected, format }, { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `investigation_${plate.replace(/[^A-Z0-9]/g, '')}_${new Date().toISOString().slice(0, 10)}.${format}`;
      anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(`${format.toUpperCase()} generated and downloaded.`);
    });
  }

  return <section className="bg-slate-800/80 p-6 rounded-3xl border border-slate-700 mb-8 space-y-5" aria-label="Investigation evidence">
    <h2 className="text-xl font-bold">Investigation Summary</h2>
    <p className="text-sm text-slate-400 break-all">Vehicle: {plate} · Reference: {reference || 'Loading…'}</p>
    {context && <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        {Object.entries({ 'First seen': time(context.summary.first_seen), 'Last seen': time(context.summary.last_seen), Detections: context.summary.detection_count, Cameras: context.summary.camera_count, Alerts: context.summary.alert_count, 'Route distance': `${context.summary.total_route_distance_km ?? 0} km`, Anomalies: context.summary.speed_anomalies, Evidence: basket.length }).map(([label, value]) => <div key={label} className="bg-slate-900 p-3 rounded-xl"><p className="text-slate-400">{label}</p><p>{value}</p></div>)}
      </div>
      <p className="text-sm">Route: {context.route.map(r => r.camera_name).join(' → ') || 'No mapped sightings'}</p>
      <p className="text-xs text-slate-400">{context.association_note}</p>
    </>}
    <label className="block text-sm">Description for next evidence item
      <textarea value={description} maxLength={2000} onChange={e => setDescription(e.target.value)} className="block w-full mt-2 p-3 bg-slate-900 rounded-lg" placeholder="Investigator observation (optional)" />
    </label>
    <button className={button} disabled={busy || !reference} onClick={() => add({ evidence_type: 'ROUTE_TRACE' })}>+ Add Route / GIS to Evidence</button>
    {context && <details><summary className="cursor-pointer">Detection results ({context.detections.length}) and related alerts ({context.alerts.length})</summary>
      <div className="max-h-80 overflow-y-auto mt-3 space-y-2">
        {context.detections.map(d => <div className="flex justify-between gap-3 p-3 bg-slate-900 rounded-lg" key={`d${d.id}`}><span>Detection #{d.id} · Camera {d.camera_id} · {d.object_class} · {time(d.timestamp)}</span><button className={button} disabled={busy} onClick={() => add({ evidence_type: 'DETECTION', detection_id: d.id })}>+ Add to Evidence</button></div>)}
        {context.alerts.map(a => <div className="flex justify-between gap-3 p-3 bg-slate-900 rounded-lg" key={`a${a.id}`}><span>Alert #{a.id} · {a.severity} · {a.message} · {time(a.timestamp)}</span><button className={button} disabled={busy} onClick={() => add({ evidence_type: 'ALERT', alert_id: a.id })}>+ Add to Evidence</button></div>)}
      </div>
    </details>}
    <h2 className="text-xl font-bold">Evidence Basket ({basket.length})</h2>
    {!basket.length && <p className="text-slate-400">Add a plate sighting, detection, alert or route to begin.</p>}
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {basket.map(e => <div key={e.id} className="bg-slate-900 p-4 rounded-xl space-y-2">
        <label className="flex gap-3"><input type="checkbox" disabled={busy} checked={selected.includes(e.id)} onChange={event => setSelected(ids => event.target.checked ? [...ids, e.id] : ids.filter(id => id !== e.id))} />#{e.id} · {e.evidence_type} · Camera {e.camera_id ?? 'Route'} · {time(e.timestamp)}</label>
        <p className="text-sm text-slate-400">{e.description || 'No description'} · {e.file_status}</p>
        <div className="flex gap-3">
          <button className={button} disabled={busy} onClick={() => run(async () => {
            const { data: item } = await api.get(`/evidence/${e.id}`);
            let url = null;
            if (item.file_status === 'AVAILABLE') { const file = await api.get(`/evidence/${e.id}/file`, { responseType: 'blob' }); url = URL.createObjectURL(file.data); }
            setPreview({ item, url });
          })}>Evidence Preview</button>
          <button className={button} disabled={busy} onClick={() => run(async () => {
            await api.delete(`/evidence/${e.id}`); setBasket(items => items.filter(item => item.id !== e.id)); setSelected(ids => ids.filter(id => id !== e.id)); setMessage('Removed from evidence.');
          })}>Remove from Evidence</button>
        </div>
      </div>)}
    </div>
    <div className="flex gap-3 flex-wrap">
      <button className={button} disabled={busy || !selected.length} onClick={() => exportFile('pdf')}>Generate Report</button>
      <button className={button} disabled={busy || !selected.length} onClick={() => exportFile('zip')}>Export Evidence Package</button>
      <span className="text-sm text-slate-400">{selected.length} selected {busy && '· Processing…'}</span>
    </div>
    <p role="status" aria-live="polite" className="text-sm text-indigo-200">{message}</p>
    {preview && <div role="dialog" aria-modal="true" aria-label="Evidence preview" className="fixed inset-0 bg-black/80 z-[1000] flex items-center justify-center p-6" onKeyDown={e => { if (e.key === 'Escape') setPreview(null); }}>
      <div className="bg-slate-800 p-6 rounded-xl max-w-3xl w-full max-h-[85vh] overflow-auto space-y-4">
        <button autoFocus className={button} onClick={() => setPreview(null)}>Close preview</button>
        <h3>Evidence #{preview.item.id} · {preview.item.evidence_type}</h3>
        {preview.url ? <img src={preview.url} alt={`Snapshot for evidence ${preview.item.id}`} className="max-h-80 mx-auto" /> : <p>{preview.item.file_status}</p>}
        <p>{preview.item.description}</p><p className="break-all text-xs">SHA-256: {preview.item.sha256 || 'No file'}</p>
        <pre className="text-xs whitespace-pre-wrap break-all">{JSON.stringify(preview.item, null, 2)}</pre>
      </div>
    </div>}
  </section>;
});
