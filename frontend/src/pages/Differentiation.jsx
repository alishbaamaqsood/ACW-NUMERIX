import React, { useState } from "react";
import api from "../utils/api";
import toast from "react-hot-toast";

const DEFAULT_X = "1.0, 1.2, 1.4, 1.6, 1.8, 2.0";
const DEFAULT_Y = "2.7183, 3.3201, 4.0552, 4.9530, 6.0496, 7.3891";

export default function Differentiation() {
  const [method, setMethod] = useState("forward");
  const [xStr, setXStr] = useState(DEFAULT_X);
  const [yStr, setYStr] = useState(DEFAULT_Y);
  const [target, setTarget] = useState("1.0");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setLoading(true);

    try {
      const x_vals = xStr.split(",").map(Number);
      const y_vals = yStr.split(",").map(Number);

      const { data } = await api.post(
        `/api/differentiation/${method}`,
        {
          x_vals,
          y_vals,
          target: parseFloat(target),
        }
      );

      setResult(data);
      toast.success("Differentiation complete");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }

    setLoading(false);
  };

  return (
    <div>
      <div className="mb-6">
        <p className="text-sm text-neon-cyan font-mono">LAB 8</p>
        <h1 className="text-3xl font-display font-bold mt-1">
          Differentiator
        </h1>
        <p className="text-slate-400 mt-2">
          Numerical differentiation using finite difference formulas
        </p>
      </div>

      <div className="flex border-b border-white/10 mb-6">
        {["forward", "backward"].map((m) => (
          <button
            key={m}
            onClick={() => {
              setMethod(m);
              setResult(null);
            }}
            className={`px-5 py-2.5 text-sm font-display capitalize transition-all ${
              method === m ? "tab-active" : "tab-inactive"
            }`}
          >
            {m === "forward"
              ? "Newton's Forward"
              : "Newton's Backward"}
          </button>
        ))}
      </div>

      <div className="glass-card neon-border p-6 mb-6">
        <div className="grid grid-cols-1 gap-4 mb-5">
          <div>
            <label className="label-text block">
              x values (equal spacing required)
            </label>

            <input
              className="input-field"
              value={xStr}
              onChange={(e) => setXStr(e.target.value)}
            />
          </div>

          <div>
            <label className="label-text block">
              y = f(x) values
            </label>

            <input
              className="input-field"
              value={yStr}
              onChange={(e) => setYStr(e.target.value)}
            />
          </div>

          <div>
            <label className="label-text block">
              Point of differentiation x =
            </label>

            <input
              className="input-field w-40"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />

            <p className="text-xs text-slate-600 mt-1 font-mono">
              {method === "forward"
                ? "Best: use a value near the start"
                : "Best: use a value near the end"}
            </p>
          </div>
        </div>

        <button
          className="btn-primary"
          onClick={compute}
          disabled={loading}
        >
          {loading ? (
            <span className="animate-spin">⟳</span>
          ) : (
            "∂"
          )}

          {loading ? "Computing..." : "Differentiate"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <p className="label-text">
                First Derivative f′(x)
              </p>

              <p className="font-mono text-2xl text-neon-cyan">
                {result.first_derivative?.toPrecision(8)}
              </p>
            </div>

            <div className="glass-card p-5">
              <p className="label-text">
                Second Derivative f″(x)
              </p>

              <p className="font-mono text-2xl text-neon-purple">
                {result.second_derivative?.toPrecision(8)}
              </p>
            </div>

            <div className="glass-card p-4">
              <p className="label-text">
                Step size h
              </p>

              <p className="font-mono text-lg text-slate-300">
                {result.h}
              </p>
            </div>

            <div className="glass-card p-4">
              <p className="label-text">
                s value
              </p>

              <p className="font-mono text-lg text-slate-300">
                {result.s?.toPrecision(6)}
              </p>
            </div>
          </div>

          {result.diff_table && (
            <div className="glass-card neon-border p-5">
              <h3 className="section-title mb-2">
                Difference Table
              </h3>

              <p className="text-xs text-slate-500 font-mono mb-4">
                Δ⁰ = y, Δ¹ = first differences, Δ² = second
                differences...
              </p>

              <div className="overflow-x-auto">
                <table className="text-left w-full">
                  <thead>
                    <tr>
                      <th className="table-header">i</th>
                      <th className="table-header">x</th>

                      {result.diff_table.map((_, i) => (
                        <th key={i} className="table-header">
                          Δ<sup>{i}</sup>y
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {result.y_vals.map((y, j) => (
                      <tr
                        key={j}
                        className={
                          j % 2 === 0
                            ? "bg-dark-800/30"
                            : ""
                        }
                      >
                        <td className="table-cell">
                          {j}
                        </td>

                        <td className="table-cell">
                          {result.x_vals[j]}
                        </td>

                        {result.diff_table.map(
                          (col, ci) => (
                            <td
                              key={ci}
                              className="table-cell"
                            >
                              {col[j] !== undefined
                                ? col[j].toPrecision(6)
                                : "—"}
                            </td>
                          )
                        )}
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