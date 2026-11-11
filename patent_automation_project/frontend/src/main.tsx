import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [file, setFile] = React.useState<File | null>(null);
  const [job, setJob] = React.useState<any>(null);
  const [message, setMessage] = React.useState('');
  const [busy, setBusy] = React.useState(false);

  async function upload() {
    if (!file) return;
    setBusy(true); setMessage('');
    try {
      const body = new FormData(); body.append('file', file);
      const res = await fetch('/api/jobs', {method:'POST', body});
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setJob(data); setMessage('Disclosure uploaded.');
    } catch (e:any) { setMessage(e.message); }
    finally { setBusy(false); }
  }
  async function runStep(step: string) {
    if (!job) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/jobs/${job.job_id}/${step}`, {method:'POST'});
      const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Request failed');
      setMessage(JSON.stringify(data, null, 2));
    } catch (e:any) { setMessage(e.message); }
    finally { setBusy(false); }
  }
  return <main>
    <header><div className="eyebrow">INTERNAL R&D WORKFLOW</div><h1>Patent Automation</h1><p>Disclosure intake · feature extraction · prior-art discovery</p></header>
    <section className="panel">
      <h2>1. Upload patent disclosure</h2>
      <p>Upload the approved corporate PPTX template.</p>
      <input type="file" accept=".pptx" onChange={e=>setFile(e.target.files?.[0] || null)} />
      <button disabled={!file || busy} onClick={upload}>{busy ? 'Working…' : 'Upload PPTX'}</button>
    </section>
    {job && <section className="panel">
      <h2>2. Process job</h2><p>Job ID: <code>{job.job_id}</code></p>
      <div className="actions">
        <button disabled={busy} onClick={()=>runStep('extract')}>Convert to Markdown</button>
        <button disabled={busy} onClick={()=>runStep('analyze')}>Extract features & queries</button>
        <button disabled={busy} onClick={()=>runStep('search')}>Run MCP search</button>
      </div>
    </section>}
    {message && <section className="panel"><h2>Activity / response</h2><pre>{message}</pre></section>}
    <footer>Starter build · Add approved identity, data governance and patent-source integrations before production use.</footer>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
