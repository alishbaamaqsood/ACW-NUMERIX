import React from "react";

const modules = [
  { id: "home",           icon: "⬡",  label: "Home",               sub: "" },
  { id: "errors",         icon: "⚠",  label: "Error Analyzer",      sub: "Lab 2" },
  { id: "rootfinder",     icon: "⌖",  label: "Root Finder",         sub: "Labs 4–5" },
  { id: "interpolation",  icon: "∿",  label: "Interpolator",        sub: "Labs 6–7" },
  { id: "differentiation",icon: "∂",  label: "Differentiator",      sub: "Lab 8" },
  { id: "integration",    icon: "∫",  label: "Integrator",          sub: "Labs 9–10" },
  { id: "ode",            icon: "dy", label: "ODE Solver",          sub: "Labs 11–12" },
  { id: "linear",         icon: "[]", label: "Linear Systems",      sub: "Lab 13" },
  { id: "chatbot",        icon: "✦",  label: "AI Assistant",        sub: "Ask NumeriX" },
];

export default function Sidebar({ active, setActive, mobileOpen, setMobileOpen }) {
  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`
          fixed top-0 left-0 h-full z-40 w-64 bg-dark-800 border-r border-white/5
          flex flex-col py-6 px-3 transition-transform duration-300
          md:translate-x-0 md:static md:z-auto
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Logo */}
        <div className="px-3 mb-8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-neon-cyan/15 border border-neon-cyan/30 flex items-center justify-center">
              <span className="text-neon-cyan font-mono font-bold text-sm">Nx</span>
            </div>
            <div>
              <h1 className="font-display font-bold text-white text-base leading-none">NumeriX</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">v1.0 · BU Karachi</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1">
          {modules.map((m) => (
            <button
              key={m.id}
              onClick={() => { setActive(m.id); setMobileOpen(false); }}
              className={`sidebar-item w-full text-left ${active === m.id ? "sidebar-active" : "sidebar-inactive"}`}
            >
              <span className={`text-base w-6 text-center font-mono ${active === m.id ? "text-neon-cyan" : "text-slate-500"}`}>
                {m.icon}
              </span>
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{m.label}</div>
                {m.sub && <div className="text-xs text-slate-600 mt-0.5">{m.sub}</div>}
              </div>
              {active === m.id && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-neon-cyan" />
              )}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 mt-6 pt-4 border-t border-white/5">
          <p className="text-xs text-slate-600 font-mono leading-relaxed">
            Numerical Analysis Project<br />
            <span className="text-neon-cyan/40">BSE-6C · Bahria University</span>
          </p>
        </div>
      </aside>
    </>
  );
}
