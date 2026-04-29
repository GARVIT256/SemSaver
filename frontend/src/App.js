import React, { useState } from "react";
import Upload from "./Upload";
import Chat from "./Chat";

export default function App() {
  const [activeTab, setActiveTab] = useState("upload");

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-3 shadow-lg">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
          <span className="text-white font-bold text-sm">S</span>
        </div>
        <h1 className="text-xl font-bold text-white tracking-tight">
          SemSaver
          <span className="ml-2 text-xs font-normal text-violet-400 bg-violet-900/40 px-2 py-0.5 rounded-full">
            Phase 1
          </span>
        </h1>
        <p className="ml-auto text-xs text-gray-500 hidden sm:block">
          AI Study Assistant · Hybrid Graph + Vector RAG
        </p>
      </header>

      {/* Tab navigation */}
      <div className="bg-gray-900 border-b border-gray-800 px-6">
        <div className="flex gap-1">
          {["upload", "chat"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3 text-sm font-medium capitalize transition-colors border-b-2 ${activeTab === tab
                  ? "border-violet-500 text-violet-400"
                  : "border-transparent text-gray-400 hover:text-gray-200"
                }`}
            >
              {tab === "upload" ? "📂 Upload" : "💬 Ask"}
            </button>
          ))}
        </div>
      </div>

      {/* Page content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {activeTab === "upload" ? <Upload /> : <Chat />}
      </main>
    </div>
  );
}
