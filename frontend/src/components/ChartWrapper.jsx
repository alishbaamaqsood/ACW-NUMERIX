import React from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart
} from "recharts";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dark-700 border border-white/10 rounded-lg p-3 shadow-xl">
        <p className="font-mono text-xs text-slate-400 mb-1">x = {typeof label === "number" ? label.toPrecision(6) : label}</p>
        {payload.map((p, i) => (
          <p key={i} className="font-mono text-xs" style={{ color: p.color }}>
            {p.name}: {typeof p.value === "number" ? p.value.toPrecision(6) : p.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function LineChartComponent({ data, xKey, lines, refX }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2535" />
        <XAxis dataKey={xKey} tick={{ fill: "#64748b", fontSize: 11, fontFamily: "JetBrains Mono" }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 11, fontFamily: "JetBrains Mono" }} />
        <Tooltip content={<CustomTooltip />} />
        {refX !== undefined && <ReferenceLine x={refX} stroke="#00F5FF" strokeDasharray="4 4" label={{ value: "root", fill: "#00F5FF", fontSize: 11 }} />}
        {lines.map((l, i) => (
          <Line key={i} type="monotone" dataKey={l.key} name={l.name}
            stroke={l.color || "#00F5FF"} strokeWidth={2}
            dot={false} activeDot={{ r: 4, fill: l.color || "#00F5FF" }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function AreaChartComponent({ data, xKey, areaKey, color = "#00F5FF" }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2535" />
        <XAxis dataKey={xKey} tick={{ fill: "#64748b", fontSize: 11, fontFamily: "JetBrains Mono" }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 11, fontFamily: "JetBrains Mono" }} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey={areaKey} stroke={color} fill="url(#areaGrad)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
