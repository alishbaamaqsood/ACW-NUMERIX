import React, { useState } from "react";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import ErrorAnalyzer from "./pages/ErrorAnalyzer";
import RootFinder from "./pages/RootFinder";
import Interpolation from "./pages/Interpolation";
import Differentiation from "./pages/Differentiation";
import Integration from "./pages/Integration";
import ODESolver from "./pages/ODESolver";
import LinearSystems from "./pages/LinearSystems";
import Chatbot from "./pages/Chatbot";

const PAGE_MAP = {
  home:            Home,
  errors:          ErrorAnalyzer,
  rootfinder:      RootFinder,
  interpolation:   Interpolation,
  differentiation: Differentiation,
  integration:     Integration,
  ode:             ODESolver,
  linear:          LinearSystems,
  chatbot:         Chatbot,
};

export default function App() {
  const [active, setActive] = useState("home");
  const [mobileOpen, setMobileOpen] = useState(false);

  const PageComponent = PAGE_MAP[active] || Home;

  return (
    <div className="min-h-screen bg-dark-900 flex">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1E2535",
            color: "#E2E8F0",
            border: "1px solid rgba(255,255,255,0.08)",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "13px",
          },
          success: { iconTheme: { primary: "#30D158", secondary: "#1E2535" } },
          error:   { iconTheme: { primary: "#FF453A", secondary: "#1E2535" } },
        }}
      />

      <Sidebar
        active={active}
        setActive={setActive}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <main className="flex-1 min-h-screen flex flex-col">
        {/* Top bar */}
        <header className="h-14 border-b border-white/5 flex items-center px-6 gap-4 sticky top-0 bg-dark-900/80 backdrop-blur-md z-20">
          <button
            className="md:hidden text-slate-400 hover:text-white transition-colors"
            onClick={() => setMobileOpen(true)}
          >
            ☰
          </button>
          <div className="flex-1 flex items-center gap-3">
            <span className="text-xs font-mono text-slate-600">numerix /</span>
            <span className="text-xs font-mono text-neon-cyan capitalize">{active}</span>
          </div>
          <div className="hidden md:flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
            <span className="text-xs font-mono text-slate-500">API connected</span>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 p-6 md:p-8 overflow-auto">
          <PageComponent setActive={setActive} />
        </div>
      </main>
    </div>
  );
}
