import React, { useState } from "react";

export default function ResultTable({ data, maxRows = 20 }) {
  const [expanded, setExpanded] = useState(false);
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  const rows = expanded ? data : data.slice(0, maxRows);

  const fmt = (v) => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") {
      return Math.abs(v) < 1e-10 ? "0" : v.toPrecision(8);
    }
    return String(v);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-white/5">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr>
              {keys.map((k) => (
                <th key={k} className="table-header whitespace-nowrap">{k}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-dark-800/30" : ""}>
                {keys.map((k) => (
                  <td key={k} className="table-cell whitespace-nowrap">{fmt(row[k])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length > maxRows && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2 text-xs font-mono text-slate-500 hover:text-neon-cyan bg-dark-800/50 transition-colors"
        >
          {expanded ? "▲ Show less" : `▼ Show all ${data.length} rows`}
        </button>
      )}
    </div>
  );
}
