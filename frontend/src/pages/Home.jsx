import React from "react";

const modules = [
  { id: "errors",          icon: "⚠",  label: "Error Analyzer",    color: "neon-cyan",   desc: "Absolute, relative, round-off & truncation errors" },
  { id: "rootfinder",      icon: "⌖",  label: "Root Finder",       color: "neon-purple", desc: "Bisection, False Position, Newton-Raphson, Fixed-Point" },
  { id: "interpolation",   icon: "∿",  label: "Interpolator",      color: "neon-blue",   desc: "Newton Forward/Backward, Divided Difference, Lagrange" },
  { id: "differentiation", icon: "∂",  label: "Differentiator",    color: "neon-cyan",   desc: "Numerical differentiation via forward & backward formulas" },
  { id: "integration",     icon: "∫",  label: "Integrator",        color: "neon-green",  desc: "Trapezoidal, Simpson's 1/3 & 3/8, Unequal Segments" },
  { id: "ode",             icon: "dy", label: "ODE Solver",        color: "neon-purple", desc: "Euler, Improved Euler, Runge-Kutta 4th Order" },
  { id: "linear",          icon: "[]", label: "Linear Systems",    color: "neon-blue",   desc: "LU Decomposition — Doolittle & Crout methods" },
];

const colorMap = {
  "neon-cyan":   { bg: "bg-neon-cyan/10",   border: "border-neon-cyan/20",   text: "text-neon-cyan",   glow: "hover:shadow-[0_0_20px_rgba(0,245,255,0.15)]" },
  "neon-purple": { bg: "bg-neon-purple/10", border: "border-neon-purple/20", text: "text-neon-purple", glow: "hover:shadow-[0_0_20px_rgba(191,90,242,0.15)]" },
  "neon-blue":   { bg: "bg-neon-blue/10",   border: "border-neon-blue/20",   text: "text-neon-blue",   glow: "hover:shadow-[0_0_20px_rgba(10,132,255,0.15)]" },
  "neon-green":  { bg: "bg-neon-green/10",  border: "border-neon-green/20",  text: "text-neon-green",  glow: "hover:shadow-[0_0_20px_rgba(48,209,88,0.15)]" },
};

export default function Home({ setActive }) {
  return (
    <div className="max-w-5xl mx-auto animate-fade-up">
      {/* Hero */}
      <div className="text-center py-16 px-4">
        <div className="inline-flex items-center gap-2 bg-neon-cyan/5 border border-neon-cyan/15 rounded-full px-4 py-1.5 mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse" />
          <span className="text-xs font-mono text-neon-cyan/70">Numerical Analysis · BSE-6C · BU Karachi</span>
        </div>

        <h1 className="font-display font-bold text-5xl md:text-6xl text-white mb-4 leading-tight">
          Numer<span className="text-neon-cyan">iX</span>
        </h1>

        <p className="text-slate-400 text-lg font-body max-w-xl mx-auto leading-relaxed mb-10">
          An interactive platform implementing 13 labs of numerical methods — 
          visualize, compute, and understand algorithms in real time.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 text-sm font-mono text-slate-500 mb-16">
          {["13 Labs Covered","7 Modules","Live Iteration Tables","Interactive Charts","Python FastAPI Backend"].map(t => (
            <span key={t} className="bg-dark-700 border border-white/5 rounded-full px-3 py-1 text-xs">
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Module Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 px-4 pb-16">
        {modules.map((m) => {
          const c = colorMap[m.color];
          return (
            <button
              key={m.id}
              onClick={() => setActive(m.id)}
              className={`
                text-left p-5 rounded-2xl border transition-all duration-300 cursor-pointer
                bg-dark-700 ${c.border} ${c.glow}
                hover:-translate-y-0.5
              `}
            >
              <div className={`w-10 h-10 ${c.bg} border ${c.border} rounded-xl flex items-center justify-center mb-4`}>
                <span className={`font-mono font-bold text-base ${c.text}`}>{m.icon}</span>
              </div>
              <h3 className={`font-display font-semibold text-base ${c.text} mb-1`}>{m.label}</h3>
              <p className="text-slate-500 text-xs font-body leading-relaxed">{m.desc}</p>
            </button>
          );
        })}
      </div>

      {/* Bottom stats */}
      <div className="grid grid-cols-3 gap-4 px-4 pb-16">
        {[
          { label: "Methods", val: "13+" },
          { label: "Labs",    val: "13" },
          { label: "Charts",  val: "7" },
        ].map(s => (
          <div key={s.label} className="glass-card neon-border p-6 text-center">
            <div className="font-display font-bold text-3xl text-neon-cyan mb-1">{s.val}</div>
            <div className="text-slate-500 text-xs font-mono uppercase tracking-wider">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
