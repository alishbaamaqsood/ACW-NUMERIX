import React, { useState } from "react";
import api from "../utils/api";
import { LineChartComponent } from "../components/ChartWrapper";
import toast from "react-hot-toast";

export default function ErrorAnalyzer() {
  const [form, setForm] = useState({ true_value: "3.14159265", approx_value: "3.14159", previous_approx: "3.1416" });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("summary");

  const compute = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/api/errors/analyze", {
        true_value: parseFloat(form.true_value),
        approx_value: parseFloat(form.approx_value),
        previous_approx: form.previous_approx ? parseFloat(form.previous_approx) : null,
      });
      setResult(data);
      toast.success("Analysis complete");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }
    setLoading(false);
  };

  const fmt = (v, d = 8) => (v !== null && v !== undefined) ? v.toPrecision(d) : "N/A";

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-cyan/60 mb-1">LAB 2</p>
        <h2 className="font-display font-bold text-2xl text-white">Error Analyzer</h2>
        <p className="text-slate-400 text-sm mt-1">Compute absolute, relative, round-off & truncation errors</p>
      </div>

      {/* Input Card */}
      <div className="glass-card neon-border p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          {[
            { key: "true_value",       label: "True Value" },
            { key: "approx_value",     label: "Approximate Value" },
            { key: "previous_approx",  label: "Previous Approx (optional)" },
          ].map(f => (
            <div key={f.key}>
              <label className="label-text block">{f.label}</label>
              <input
                className="input-field"
                value={form[f.key]}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                placeholder="e.g. 3.14159"
              />
            </div>
          ))}
        </div>
        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "⚡"}
          {loading ? "Computing..." : "Analyze Errors"}
        </button>
      </div>

      {result && (
        <>
          {/* Tabs */}
          <div className="flex border-b border-white/10 mb-6">
            {["summary", "roundoff", "truncation"].map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-5 py-2.5 text-sm font-display capitalize transition-all ${tab === t ? "tab-active" : "tab-inactive"}`}>
                {t === "roundoff" ? "Round-Off Demo" : t === "truncation" ? "Truncation Demo" : "Summary"}
              </button>
            ))}
          </div>

          {tab === "summary" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { label: "True Value",                  val: fmt(result.true_value) },
                { label: "Approximate Value",           val: fmt(result.approx_value) },
                { label: "Absolute Error",              val: fmt(result.absolute_error) },
                { label: "Relative Error",              val: fmt(result.relative_error) },
                { label: "% Relative Error",            val: result.percent_relative_error ? fmt(result.percent_relative_error) + "%" : "N/A" },
                { label: "Approx % Relative Error",     val: result.approx_percent_relative_error ? fmt(result.approx_percent_relative_error) + "%" : "N/A" },
              ].map(r => (
                <div key={r.label} className="glass-card p-4 flex justify-between items-center">
                  <span className="text-slate-400 text-sm font-display">{r.label}</span>
                  <span className="font-mono text-neon-cyan text-sm">{r.val}</span>
                </div>
              ))}
            </div>
          )}

          {tab === "roundoff" && (
            <div className="glass-card neon-border p-6">
              <h3 className="section-title mb-1">Round-Off Error Demo</h3>
              <p className="text-slate-500 text-xs mb-5 font-mono">x = 1 → x/3×3 repeated — should stay 1 but drifts due to floating-point</p>
              <LineChartComponent
                data={result.roundoff_demo.map(r => ({ step: r.step, error: r.error, value: r.value }))}
                xKey="step"
                lines={[
                  { key: "error", name: "Round-Off Error", color: "#BF5AF2" },
                  { key: "value", name: "Computed Value",  color: "#00F5FF" },
                ]}
              />
            </div>
          )}

          {tab === "truncation" && (
            <div className="glass-card neon-border p-6">
              <h3 className="section-title mb-1">Truncation Error Demo</h3>
              <p className="text-slate-500 text-xs mb-5 font-mono">Taylor series for e^x — error decreases as more terms added</p>
              <LineChartComponent
                data={result.truncation_demo.map(r => ({ terms: r.terms, error: r.truncation_error, approx: r.approx }))}
                xKey="terms"
                lines={[
                  { key: "error",  name: "Truncation Error", color: "#BF5AF2" },
                  { key: "approx", name: "Approx e^x",       color: "#00F5FF" },
                ]}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
