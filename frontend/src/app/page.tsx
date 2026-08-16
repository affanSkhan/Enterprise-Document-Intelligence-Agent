"use client";

import { useState } from 'react';
import DocumentLibrary from '@/components/DocumentLibrary';
import UploadPanel from '@/components/UploadPanel';
import ChatInterface from '@/components/ChatInterface';
import AgentActions from '@/components/AgentActions';

type Tab = 'library' | 'chat' | 'agents';
const tabs: Tab[] = ['library', 'chat', 'agents'];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('library');

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-100 font-sans selection:bg-indigo-500/30">
      <header className="border-b border-white/10 bg-black/40 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold tracking-tight">DocIntel<span className="text-indigo-400">Agent</span></h1>
          </div>
          <nav className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === tab ? 'bg-indigo-500/20 text-indigo-300' : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/5'}`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {activeTab === 'library' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 fade-in">
            <div className="lg:col-span-2 space-y-6"><DocumentLibrary /></div>
            <div className="space-y-6"><UploadPanel /></div>
          </div>
        )}
        {activeTab === 'chat' && <div className="max-w-4xl mx-auto h-[calc(100vh-10rem)] fade-in"><ChatInterface /></div>}
        {activeTab === 'agents' && <div className="max-w-5xl mx-auto fade-in"><AgentActions /></div>}
      </main>
    </div>
  );
}
