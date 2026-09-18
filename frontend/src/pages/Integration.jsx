import React, { useState } from "react";
import api from "../utils/api";
import { AreaChartComponent } from "../components/ChartWrapper";
import toast from "react-hot-toast";

const METHODS = [
  { id: "trapezoidal",          label: "Trapezoidal",      color: "#00F5FF" },
  { id: "simpson_third",        label: "Simpson's 1/3",    color: "#BF5AF2" },
  { id: "simpson_three_eighth", label: "Simpson's 3/8",    color: "#0A84FF" },
  { id: "unequal_segments",     label: "Unequal Segments", color: "#30D158" },
];

export default function Integration() {
  const [method, setMethod] = useState("trapezoidal");
  const [mode, setMode] = useState("function"); // "function" or "table"
  const [fx, setFx] = useState("x**2");
  const [a, setA] = useState("0");
  const [b, setB] = useState("1");
  const [n, setN] = useState("4");
  const [xStr, setXStr] = useState("0, 0.25, 0.5, 0.75, 1.0");
  const [yStr, setYStr] = useState("0, 0.0625, 0.25, 0.5625, 1.0");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setLoading(true);
    try {
      let payload = {};
      if (method === "unequal_segments" || mode === "table") {
        payload = {
          x_vals: xStr.split(",").map(Number),
          y_vals: yStr.split(",").map(Number),
        };
      } else {
        payload = { fx, a: parseFloat(a), b: parseFloat(b), n: parseInt(n) };
      }
      const { data } = await api.post(`/api/integration/${method}`, payload);
      setResult(data);
      toast.success(`Area ≈ ${data.result?.toPrecision(8)}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }
    setLoading(false);
  };

  const activeColor = METHODS.find(m => m.id === method)?.color || "#00F5FF";
  const chartData = result?.x_vals?.map((x, i) => ({ x, y: result.y_vals[i] })) || [];

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-green/60 mb-1">LABS 9–10</p>
        <h2 className="font-display font-bold text-2xl text-white">Integrator</h2>
        <p className="text-slate-400 text-sm mt-1">Numerical integration using quadrature rules</p>
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
        {method !== "unequal_segments" && (
          <div className="flex gap-3 mb-5">
            <button onClick={() => setMode("function")} className={mode === "function" ? "btn-primary py-1.5 px-4 text-sm" : "btn-secondary"}>f(x) function</button>
            <button onClick={() => setMode("table")}    className={mode === "table"    ? "btn-primary py-1.5 px-4 text-sm" : "btn-secondary"}>tabular data</button>
          </div>
        )}

        {(mode === "function" && method !== "unequal_segments") ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            <div className="col-span-2">
              <label className="label-text block">f(x)</label>
              <input className="input-field" value={fx} onChange={e => setFx(e.target.value)} placeholder="x**2" />
            </div>
            <div>
              <label className="label-text block">a (lower limit)</label>
              <input className="input-field" value={a} onChange={e => setA(e.target.value)} />
            </div>
            <div>
              <label className="label-text block">b (upper limit)</label>
              <input className="input-field" value={b} onChange={e => setB(e.target.value)} />
            </div>
            <div>
              <label className="label-text block">n (intervals)</label>
              <input className="input-field" value={n} onChange={e => setN(e.target.value)} />
              <p className="text-xs text-slate-600 mt-1 font-mono">
                {method === "simpson_third" ? "must be even" : method === "simpson_three_eighth" ? "must be mult. of 3" : ""}
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 mb-5">
            <div>
              <label className="label-text block">x values (comma-separated)</label>
              <input className="input-field" value={xStr} onChange={e => setXStr(e.target.value)} />
            </div>
            <div>
              <label className="label-text block">y = f(x) values</label>
              <input className="input-field" value={yStr} onChange={e => setYStr(e.target.value)} />
            </div>
          </div>
        )}

        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "∫"}
          {loading ? "Computing..." : "Integrate"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="glass-card p-5 flex items-center gap-8">
            <div>
              <p className="label-text">∫ f(x) dx ≈</p>
              <p className="font-mono text-3xl text-neon-cyan">{result.result?.toPrecision(10)}</p>
            </div>
            {result.h && <div>
              <p className="label-text">Step h</p>
              <p className="font-mono text-lg text-slate-300">{result.h}</p>
            </div>}
            {result.n && <div>
              <p className="label-text">Intervals n</p>
              <p className="font-mono text-lg text-slate-300">{result.n}</p>
            </div>}
          </div>

          {chartData.length > 0 && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Area Under Curve</h3>
              <AreaChartComponent data={chartData} xKey="x" areaKey="y" color={activeColor} />
            </div>
          )}

          {result.segments && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-4">Segment Breakdown</h3>
              <div className="overflow-hidden rounded-xl border border-white/5">
                <table className="w-full text-left">
                  <thead>
                    <tr>
                      {Object.keys(result.segments[0]).map(k => <th key={k} className="table-header">{k}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {result.segments.map((s, i) => (
                      <tr key={i} className={i % 2 === 0 ? "bg-dark-800/30" : ""}>
                        {Object.values(s).map((v, j) => (
                          <td key={j} className="table-cell">{typeof v === "number" ? v.toPrecision(6) : v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
