import React, { useState } from "react";
import api from "../utils/api";
import ResultTable from "../components/ResultTable";
import { LineChartComponent } from "../components/ChartWrapper";
import toast from "react-hot-toast";

const METHODS = [
  { id: "euler",          label: "Euler's Method" },
  { id: "improved_euler", label: "Improved Euler (Heun)" },
  { id: "rk4",            label: "Runge-Kutta 4" },
];

export default function ODESolver() {
  const [method, setMethod] = useState("rk4");
  const [form, setForm] = useState({ dydx: "x + y", x0: "0", y0: "1", h: "0.1", xn: "1" });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setLoading(true);
    try {
      const { data } = await api.post(`/api/ode/${method}`, {
        dydx: form.dydx,
        x0: parseFloat(form.x0),
        y0: parseFloat(form.y0),
        h: parseFloat(form.h),
        xn: parseFloat(form.xn),
      });
      setResult(data);
      toast.success(`y(${form.xn}) ≈ ${data.result?.toPrecision(8)}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }
    setLoading(false);
  };

  const chartData = result?.steps?.map(s => ({ x: s.x, y: s.y, y_new: s.y_new })) || [];

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-purple/60 mb-1">LABS 11–12</p>
        <h2 className="font-display font-bold text-2xl text-white">ODE Solver</h2>
        <p className="text-slate-400 text-sm mt-1">Solve dy/dx = f(x, y) with initial conditions</p>
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
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-5">
          <div className="col-span-2 md:col-span-3">
            <label className="label-text block">dy/dx = f(x, y)</label>
            <input className="input-field" value={form.dydx} onChange={e => setForm({...form, dydx: e.target.value})} placeholder="x + y" />
            <p className="text-xs text-slate-600 mt-1 font-mono">Use: x, y, sin(x), exp(x), log(x), etc.</p>
          </div>
          {[
            { k: "x0", l: "x₀ (initial x)" },
            { k: "y0", l: "y₀ = y(x₀)" },
            { k: "h",  l: "Step size h" },
            { k: "xn", l: "xₙ (final x)" },
          ].map(f => (
            <div key={f.k}>
              <label className="label-text block">{f.l}</label>
              <input className="input-field" value={form[f.k]} onChange={e => setForm({...form, [f.k]: e.target.value})} />
            </div>
          ))}
        </div>
        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "dy"}
          {loading ? "Solving..." : "Solve ODE"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="glass-card p-5 flex items-center gap-8">
            <div>
              <p className="label-text">y({form.xn}) ≈</p>
              <p className="font-mono text-3xl text-neon-cyan">{result.result?.toPrecision(10)}</p>
            </div>
            <div>
              <p className="label-text">Steps</p>
              <p className="font-mono text-2xl text-neon-purple">{result.steps?.length}</p>
            </div>
          </div>

          {chartData.length > 0 && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Solution Curve y(x)</h3>
              <LineChartComponent
                data={chartData}
                xKey="x"
                lines={[
                  { key: "y",     name: "y (current)", color: "#00F5FF" },
                  { key: "y_new", name: "y (next)",    color: "#BF5AF2" },
                ]}
              />
            </div>
          )}

          <div className="glass-card neon-border p-5">
            <h3 className="section-title mb-4">Step-by-Step Table</h3>
            <ResultTable data={result.steps} />
          </div>
        </div>
      )}
    </div>
  );
}
