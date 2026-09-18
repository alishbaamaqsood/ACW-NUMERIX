import React, { useState } from "react";
import api from "../utils/api";
import ResultTable from "../components/ResultTable";
import { LineChartComponent } from "../components/ChartWrapper";
import toast from "react-hot-toast";

const METHODS = [
  { id: "bisection",       label: "Bisection",        fields: ["fx","a","b","tol","max_iter"] },
  { id: "false_position",  label: "False Position",   fields: ["fx","a","b","tol","max_iter"] },
  { id: "newton_raphson",  label: "Newton-Raphson",   fields: ["fx","dfx","x0","tol","max_iter"] },
  { id: "fixed_point",     label: "Fixed-Point",      fields: ["gx","x0","tol","max_iter"] },
];

const DEFAULTS = {
  bisection:      { fx: "x**3 - x - 2", a: "1", b: "2", tol: "1e-6", max_iter: "50" },
  false_position: { fx: "x**3 - x - 2", a: "1", b: "2", tol: "1e-6", max_iter: "50" },
  newton_raphson: { fx: "x**3 - x - 2", dfx: "3*x**2 - 1", x0: "1.5", tol: "1e-6", max_iter: "50" },
  fixed_point:    { gx: "(x + 2/x**2)**0.5", x0: "1.5", tol: "1e-6", max_iter: "50" },
};

const FIELD_LABELS = {
  fx: "f(x)", dfx: "f′(x)", gx: "g(x)", a: "a (lower bound)",
  b: "b (upper bound)", x0: "x₀ (initial guess)", tol: "Tolerance", max_iter: "Max Iterations",
};

export default function RootFinder() {
  const [method, setMethod] = useState("bisection");
  const [form, setForm] = useState(DEFAULTS.bisection);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const switchMethod = (m) => {
    setMethod(m);
    setForm(DEFAULTS[m]);
    setResult(null);
  };

  const compute = async () => {
    setLoading(true);
    try {
      const payload = { ...form };
      ["a","b","x0","tol","max_iter"].forEach(k => { if (payload[k] !== undefined) payload[k] = parseFloat(payload[k]); });
      payload.max_iter = parseInt(payload.max_iter || 50);
      const { data } = await api.post(`/api/roots/${method}`, payload);
      setResult(data);
      toast.success(`Root found: ${data.root?.toPrecision(8)}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Computation error");
    }
    setLoading(false);
  };

  const m = METHODS.find(x => x.id === method);
  const chartData = result?.iterations?.map(r => ({
    iter: r.iter,
    c: r.c ?? r.x_new ?? r.x,
    error: r.error,
  }));

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-purple/60 mb-1">LABS 4–5</p>
        <h2 className="font-display font-bold text-2xl text-white">Root Finder</h2>
        <p className="text-slate-400 text-sm mt-1">Solve f(x) = 0 using bracketing and open methods</p>
      </div>

      {/* Method Tabs */}
      <div className="flex flex-wrap border-b border-white/10 mb-6">
        {METHODS.map(m2 => (
          <button key={m2.id} onClick={() => switchMethod(m2.id)}
            className={`px-4 py-2.5 text-sm font-display transition-all ${method === m2.id ? "tab-active" : "tab-inactive"}`}>
            {m2.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="glass-card neon-border p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {m.fields.map(f => (
            <div key={f}>
              <label className="label-text block">{FIELD_LABELS[f] || f}</label>
              <input className="input-field" value={form[f] || ""}
                onChange={e => setForm({ ...form, [f]: e.target.value })}
                placeholder={f === "fx" ? "e.g. x**3 - x - 2" : ""} />
              {(f === "fx" || f === "gx" || f === "dfx") && (
                <p className="text-xs text-slate-600 mt-1 font-mono">Use: x, sin(x), cos(x), exp(x), log(x), sqrt(x)</p>
              )}
            </div>
          ))}
        </div>
        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "⌖"}
          {loading ? "Computing..." : "Find Root"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Result badge */}
          <div className="glass-card p-5 flex flex-wrap items-center gap-6">
            <div>
              <p className="label-text">Root</p>
              <p className="font-mono text-2xl text-neon-cyan">{result.root?.toPrecision(10)}</p>
            </div>
            <div>
              <p className="label-text">Iterations</p>
              <p className="font-mono text-2xl text-neon-purple">{result.iterations?.length}</p>
            </div>
            <div>
              <p className="label-text">Converged</p>
              <p className={`font-mono text-lg ${result.converged ? "text-neon-green" : "text-red-400"}`}>
                {result.converged ? "✓ Yes" : "✗ No"}
              </p>
            </div>
          </div>

          {/* Convergence chart */}
          {chartData && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Convergence — Root Approximation per Iteration</h3>
              <LineChartComponent data={chartData} xKey="iter"
                lines={[
                  { key: "c",     name: "Root Approx", color: "#00F5FF" },
                  { key: "error", name: "Error",       color: "#BF5AF2" },
                ]}
              />
            </div>
          )}

          {/* Iteration table */}
          <div className="glass-card neon-border p-5">
            <h3 className="section-title mb-4">Iteration Table</h3>
            <ResultTable data={result.iterations} />
          </div>
        </div>
      )}
    </div>
  );
}
