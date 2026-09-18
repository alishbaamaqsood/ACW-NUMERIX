import React, { useState } from "react";
import api from "../utils/api";
import toast from "react-hot-toast";

const DEFAULT_3x3 = { matrix: [[2,1,-1],[4,3,3],[2,-2,1]], vector: [8,18,8] };

export default function LinearSystems() {
  const [method, setMethod] = useState("doolittle");
  const [size, setSize] = useState(3);
  const [matrix, setMatrix] = useState(DEFAULT_3x3.matrix);
  const [vector, setVector] = useState(DEFAULT_3x3.vector);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const setMatrixSize = (s) => {
    setSize(s);
    setMatrix(Array.from({length: s}, (_, i) => Array.from({length: s}, (_, j) => (i === j ? 1 : 0))));
    setVector(Array(s).fill(0));
    setResult(null);
  };

  const updateCell = (i, j, v) => {
    const m = matrix.map(r => [...r]);
    m[i][j] = parseFloat(v) || 0;
    setMatrix(m);
  };

  const updateVec = (i, v) => {
    const vec = [...vector];
    vec[i] = parseFloat(v) || 0;
    setVector(vec);
  };

  const compute = async () => {
    setLoading(true);
    try {
      const { data } = await api.post(`/api/linear/${method}`, { matrix, vector });
      setResult(data);
      toast.success("System solved");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Error");
    }
    setLoading(false);
  };

  const fmtMat = (mat) => mat?.map((row, i) => (
    <tr key={i}>
      {row.map((v, j) => (
        <td key={j} className="table-cell text-center">{v?.toPrecision(6)}</td>
      ))}
    </tr>
  ));

  return (
    <div className="animate-fade-up max-w-4xl">
      <div className="mb-8">
        <p className="text-xs font-mono text-neon-blue/60 mb-1">LAB 13</p>
        <h2 className="font-display font-bold text-2xl text-white">Linear Systems — LU Decomposition</h2>
        <p className="text-slate-400 text-sm mt-1">Solve Ax = b using Doolittle's or Crout's method</p>
      </div>

      <div className="flex border-b border-white/10 mb-6">
        {["doolittle","crout"].map(m => (
          <button key={m} onClick={() => { setMethod(m); setResult(null); }}
            className={`px-5 py-2.5 text-sm font-display capitalize transition-all ${method === m ? "tab-active" : "tab-inactive"}`}>
            {m === "doolittle" ? "Doolittle (L diagonal = 1)" : "Crout (U diagonal = 1)"}
          </button>
        ))}
      </div>

      <div className="glass-card neon-border p-6 mb-6">
        {/* Size selector */}
        <div className="flex items-center gap-3 mb-6">
          <span className="label-text">Matrix size:</span>
          {[2,3,4].map(s => (
            <button key={s} onClick={() => setMatrixSize(s)}
              className={size === s ? "btn-primary py-1.5 px-4 text-sm" : "btn-secondary"}>
              {s}×{s}
            </button>
          ))}
        </div>

        {/* Matrix input */}
        <div className="mb-5 overflow-x-auto">
          <p className="label-text mb-3">Matrix A | Vector b</p>
          <div className="inline-flex flex-col gap-2">
            {Array.from({length: size}, (_, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-slate-600 font-mono text-xs w-4">[{i}]</span>
                {Array.from({length: size}, (_, j) => (
                  <input key={j}
                    className="w-16 bg-dark-800 border border-white/10 rounded-lg px-2 py-1.5 text-center font-mono text-sm text-slate-200 focus:outline-none focus:border-neon-cyan/50"
                    value={matrix[i]?.[j] ?? 0}
                    onChange={e => updateCell(i, j, e.target.value)}
                  />
                ))}
                <span className="text-slate-600 font-mono text-sm px-2">|</span>
                <input
                  className="w-16 bg-dark-800 border border-neon-cyan/20 rounded-lg px-2 py-1.5 text-center font-mono text-sm text-neon-cyan focus:outline-none focus:border-neon-cyan/50"
                  value={vector[i] ?? 0}
                  onChange={e => updateVec(i, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>

        <button className="btn-primary" onClick={compute} disabled={loading}>
          {loading ? <span className="animate-spin">⟳</span> : "[]"}
          {loading ? "Decomposing..." : "Solve with LU"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Solution */}
          <div className="glass-card p-5">
            <p className="label-text mb-3">Solution x =</p>
            <div className="flex flex-wrap gap-4">
              {result.x.map((v, i) => (
                <div key={i} className="bg-neon-cyan/5 border border-neon-cyan/20 rounded-xl px-5 py-3 text-center">
                  <p className="text-xs text-slate-500 font-mono mb-1">x{i+1}</p>
                  <p className="font-mono text-xl text-neon-cyan">{v.toPrecision(8)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* L and U matrices */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: "L matrix (Lower Triangular)", mat: result.L, color: "neon-purple" },
              { label: "U matrix (Upper Triangular)", mat: result.U, color: "neon-blue" },
            ].map(({ label, mat, color }) => (
              <div key={label} className="glass-card neon-border p-5">
                <h3 className={`font-display font-semibold text-sm text-${color} mb-4`}>{label}</h3>
                <div className="overflow-x-auto">
                  <table className="text-left">
                    <thead>
                      <tr>{mat[0].map((_, j) => <th key={j} className="table-header w-20">col {j+1}</th>)}</tr>
                    </thead>
                    <tbody>{fmtMat(mat)}</tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>

          {/* y vector */}
          <div className="glass-card p-5">
            <p className="label-text mb-3">Intermediate y (from Ly = b)</p>
            <div className="flex flex-wrap gap-3">
              {result.y.map((v, i) => (
                <div key={i} className="bg-dark-600 rounded-lg px-4 py-2 text-center">
                  <p className="text-xs text-slate-500 font-mono mb-0.5">y{i+1}</p>
                  <p className="font-mono text-slate-300">{v.toPrecision(6)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
