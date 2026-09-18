import React, { useState } from "react";
import api from "../utils/api";
import ResultTable from "../components/ResultTable";
import { LineChartComponent } from "../components/ChartWrapper";
import toast from "react-hot-toast";

const METHODS = [
  { id: "newton_forward",    label: "Newton Forward" },
  { id: "newton_backward",   label: "Newton Backward" },
  { id: "divided_difference",label: "Divided Difference" },
  { id: "lagrange",          label: "Lagrange" },
];

const DEFAULT_X = "1, 2, 3, 4, 5";
const DEFAULT_Y = "1, 4, 9, 16, 25";
const DEFAULT_T = "2.5";

export default function Interpolation() {
  const [method, setMethod] = useState("newton_forward");
  const [xStr, setXStr] = useState(DEFAULT_X);
  const [yStr, setYStr] = useState(DEFAULT_Y);
  const [target, setTarget] = useState(DEFAULT_T);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setLoading(true);
    try {
      const x_vals = xStr.split(",").map(Number);
      const y_vals = yStr.split(",").map(Number);
      const { data } = await api.post(`/api/interpolation/${method}`, {
        x_vals, y_vals, target: parseFloat(target)
      });
      setResult(data);
      toast.success(`Interpolated value: ${data.result?.toPrecision(8)}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }
    setLoading(false);
  };

  const x_arr = xStr.split(",").map(Number);
  const y_arr = yStr.split(",").map(Number);
  const chartData = x_arr.map((x, i) => ({ x, y: y_arr[i] }));
  if (result) chartData.push({ x: parseFloat(target), y: result.result, interpolated: result.result });

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-blue/60 mb-1">LABS 6–7</p>
        <h2 className="font-display font-bold text-2xl text-white">Interpolator</h2>
        <p className="text-slate-400 text-sm mt-1">Estimate intermediate values from tabular data</p>
      </div>

      <div className="flex flex-wrap border-b border-white/10 mb-6">
        {METHODS.map(m => (
          <button key={m.id} onClick={() => { setMethod(m.id); setResult(null); }}
            className={`px-4 py-2.5 text-sm font-display transition-all ${method === m.id ? "tab-active" : "tab-inactive"}`}>
            {m.label}
          </button>
        ))}
      </div>

      <div className="glass-card neon-border p-6 mb-6">
        <div className="grid grid-cols-1 gap-4 mb-5">
          <div>
            <label className="label-text block">x values (comma-separated)</label>
            <input className="input-field" value={xStr} onChange={e => setXStr(e.target.value)} placeholder="1, 2, 3, 4, 5" />
          </div>
          <div>
            <label className="label-text block">y = f(x) values (comma-separated)</label>
            <input className="input-field" value={yStr} onChange={e => setYStr(e.target.value)} placeholder="1, 4, 9, 16, 25" />
          </div>
          <div>
            <label className="label-text block">Target x to interpolate</label>
            <input className="input-field w-48" value={target} onChange={e => setTarget(e.target.value)} placeholder="2.5" />
          </div>
        </div>
        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "∿"}
          {loading ? "Computing..." : "Interpolate"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="glass-card p-5 flex items-center gap-6">
            <div>
              <p className="label-text">Interpolated Value at x = {target}</p>
              <p className="font-mono text-2xl text-neon-cyan">{result.result?.toPrecision(10)}</p>
            </div>
          </div>

          <div className="glass-card neon-border p-5">
            <h3 className="section-title mb-4">Data Points + Interpolated Value</h3>
            <LineChartComponent
              data={x_arr.map((x, i) => ({ x, y: y_arr[i] }))}
              xKey="x"
              lines={[{ key: "y", name: "f(x)", color: "#00F5FF" }]}
              refX={parseFloat(target)}
            />
          </div>

          {result.steps && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Computation Steps</h3>
              <ResultTable data={result.steps} />
            </div>
          )}

          {result.basis_values && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Lagrange Basis Values</h3>
              <ResultTable data={result.basis_values} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
