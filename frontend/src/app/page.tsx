"use client";
import { useState, useRef } from "react";
import { FlaskConical, Upload, Link2, Play, Loader2, CheckCircle2, Circle, XCircle } from "lucide-react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const AGENTS = [
  { role: "ingestion", label: "Paper Ingestion" },
  { role: "methodology", label: "Methodology Extraction" },
  { role: "planning", label: "Implementation Planning" },
  { role: "code_gen", label: "Code Generation" },
  { role: "reproducibility", label: "Reproducibility Check" },
];

const DEMO = `Title: Attention Is All You Need
Authors: Vaswani et al., NeurIPS 2017

Abstract: The Transformer model replaces recurrent layers entirely with attention mechanisms for sequence-to-sequence tasks.

Methodology:
- Encoder + Decoder, each with N=6 identical layers
- d_model=512, num_heads=8, d_ff=2048, dropout=0.1
- Adam optimizer β1=0.9, β2=0.98, ε=1e-9, warmup_steps=4000
- Label smoothing ε_ls=0.1
- WMT 2014 EN-DE: 4.5M sentence pairs → BLEU 28.4 (base)
- WMT 2014 EN-FR: 36M pairs → BLEU 41.0 (big ensemble)`;

export default function Home() {
  const [tab, setTab] = useState<"paste" | "upload">("paste");
  const [text, setText] = useState(DEMO);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<Record<string, any>>({});
  const [progress, setProgress] = useState(0);
  const [job, setJob] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    setLoading(true);
    setSteps({});
    setProgress(0);
    setJob(null);
    const fd = new FormData();
    fd.append("paper_text", text);
    const res = await axios.post(`${API}/jobs`, fd);
    const id = res.data.job_id;
    setJobId(id);

    const es = new EventSource(`${API}/jobs/${id}/stream`);
    es.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.done) {
        es.close();
        setLoading(false);
        axios.get(`${API}/jobs/${id}`).then(r => setJob(r.data));
        return;
      }
      setSteps(prev => ({ ...prev, [d.step]: d }));
      setProgress(d.progress_pct);
    };
    es.onerror = () => { es.close(); setLoading(false); };
  };

  return (
    <div className="min-h-screen bg-[#0d1117] text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-4 flex items-center gap-3">
        <FlaskConical className="w-6 h-6 text-purple-400" />
        <h1 className="text-lg font-semibold">Research-to-Prototype Agent</h1>
        <span className="ml-auto text-xs text-gray-500">Autonomously turns papers into runnable code</span>
      </header>

      <div className="max-w-6xl mx-auto p-8 grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Input panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <div className="flex gap-2 mb-4">
              {(["paste", "upload"] as const).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? "bg-purple-600 text-white" : "text-gray-400 hover:text-white"}`}>
                  {t === "paste" ? "Paste Text" : "Upload PDF"}
                </button>
              ))}
            </div>

            {tab === "paste" ? (
              <textarea
                className="w-full h-64 bg-[#0d1117] border border-gray-700 rounded-lg p-3 text-sm text-gray-200 font-mono resize-none focus:outline-none focus:border-purple-500"
                value={text} onChange={e => setText(e.target.value)}
                placeholder="Paste paper abstract + methodology..."
              />
            ) : (
              <div onClick={() => fileRef.current?.click()}
                className="h-64 border-2 border-dashed border-gray-700 rounded-lg flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-purple-500 transition-colors">
                <Upload className="w-8 h-8 text-gray-500" />
                <p className="text-sm text-gray-400">Click to upload PDF or .txt</p>
                <input ref={fileRef} type="file" className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) f.text().then(setText); }} />
              </div>
            )}

            <button onClick={submit} disabled={loading || !text.trim()}
              className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading ? "Running pipeline…" : "Run Research Pipeline"}
            </button>

            {(loading || progress > 0) && (
              <div className="mt-3">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Progress</span><span>{progress.toFixed(0)}%</span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full">
                  <div className="h-full bg-purple-500 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}
          </div>

          {/* Platform guarantees */}
          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Safety Guarantees</p>
            {["Never claims success without tests passing", "All assumptions clearly labeled", "Every decision traced to paper passage", "Human approval before code execution"].map(g => (
              <div key={g} className="flex items-start gap-2 mb-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-400 mt-0.5 shrink-0" />
                <p className="text-xs text-gray-400">{g}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline + results */}
        <div className="lg:col-span-3 space-y-4">
          {/* Agent timeline */}
          <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Agent Pipeline</p>
            <div className="space-y-2">
              {AGENTS.map((a, i) => {
                const s = steps[a.role];
                const done = !!s;
                const active = loading && !done && AGENTS[i - 1] ? !!steps[AGENTS[i - 1].role] : false;
                return (
                  <div key={a.role} className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${active ? "border-purple-500/40 bg-purple-500/5" : "border-gray-800 bg-[#0d1117]"}`}>
                    <div className="mt-0.5">
                      {done ? <CheckCircle2 className="w-4 h-4 text-green-400" /> :
                       active ? <Loader2 className="w-4 h-4 text-purple-400 animate-spin" /> :
                       <Circle className="w-4 h-4 text-gray-700" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between">
                        <span className="text-sm font-medium">{a.label}</span>
                        {s?.confidence !== undefined && (
                          <span className="text-xs text-gray-500">{(s.confidence * 100).toFixed(0)}% conf</span>
                        )}
                      </div>
                      {s?.summary && <p className="text-xs text-gray-400 mt-0.5">{s.summary}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Reproducibility report */}
          {job?.report && (
            <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Reproducibility Report</p>
              <div className="flex items-center gap-4 mb-4">
                <div className="text-3xl font-bold text-purple-400">
                  {(job.report.overall_score * 100).toFixed(0)}%
                </div>
                <div>
                  <p className="text-sm text-white font-medium">Overall Score</p>
                  <div className="flex gap-3 text-xs mt-1">
                    <span className={job.report.code_ran ? "text-green-400" : "text-red-400"}>
                      {job.report.code_ran ? "✓ Code ran" : "✗ Code failed"}
                    </span>
                    <span className={job.report.tests_passed ? "text-green-400" : "text-red-400"}>
                      {job.report.tests_passed ? "✓ Tests passed" : "✗ Tests failed"}
                    </span>
                  </div>
                </div>
              </div>
              {job.report.comparisons?.slice(0, 4).map((c: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-t border-gray-800 text-sm">
                  <span className="text-gray-300">{c.metric}</span>
                  <span className="text-gray-500">Paper: {c.paper_value}</span>
                  <span className="text-gray-300">Got: {c.reproduced_value}</span>
                  <span className={c.within_tolerance ? "text-green-400" : "text-red-400"}>
                    {c.within_tolerance ? "✓" : "✗"}
                  </span>
                </div>
              ))}
              {job.report.recommendation && (
                <p className="mt-3 text-xs text-gray-400 bg-[#0d1117] rounded-lg p-3">{job.report.recommendation}</p>
              )}
            </div>
          )}

          {/* Methodology ambiguities */}
          {job?.methodology?.ambiguities?.length > 0 && (
            <div className="bg-[#161b22] rounded-xl border border-yellow-900/40 p-5">
              <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-3">
                Ambiguities Detected ({job.methodology.ambiguities.length})
              </p>
              {job.methodology.ambiguities.map((a: any, i: number) => (
                <div key={i} className="flex items-start gap-2 mb-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${a.severity === "blocking" ? "bg-red-900/40 text-red-400" : "bg-yellow-900/40 text-yellow-400"}`}>
                    {a.severity}
                  </span>
                  <p className="text-xs text-gray-300">{a.detail}</p>
                </div>
              ))}
            </div>
          )}

          {/* Code artifacts */}
          {job?.artifacts?.length > 0 && (
            <div className="bg-[#161b22] rounded-xl border border-gray-800 p-5">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Generated Files ({job.artifacts.length})
              </p>
              <div className="grid grid-cols-2 gap-2">
                {job.artifacts.map((a: any) => (
                  <a key={a.id}
                    href={`${API}/jobs/${jobId}/artifacts/${a.id}/download`}
                    className="flex items-center gap-2 p-2 rounded-lg bg-[#0d1117] border border-gray-800 hover:border-purple-500/50 text-xs text-gray-300 transition-colors"
                    download>
                    <span className="text-purple-400">↓</span> {a.path}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
