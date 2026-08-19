"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { TABS } from "@/types";
import { OverviewTab } from "./tabs/Overview";
import { AIResearchTab } from "./tabs/AIResearch";
import { WhyItMovedTab } from "./tabs/WhyItMoved";
import { StockDoctorTab } from "./tabs/StockDoctor";
import { NewsTab } from "./tabs/News";
import { EvidenceTab } from "./tabs/Evidence";
import { clsx } from "clsx";
import { Disclaimer } from "@/components/dashboard/Disclaimer";

const TabComponents: Record<string, React.FC<{ symbol: string }>> = {
  overview: OverviewTab,
  research: AIResearchTab,
  movement: WhyItMovedTab,
  doctor: StockDoctorTab,
  news: NewsTab,
  evidence: EvidenceTab,
};

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.ticker as string;
  const [activeTab, setActiveTab] = useState("overview");

  if (!symbol) return null;

  const TabComponent = TabComponents[activeTab];

  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text pb-24">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-terminal-bg/95 backdrop-blur border-b border-terminal-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <a
                href="/"
                className="flex items-center gap-2 text-terminal-text hover:text-terminal-accent transition-colors"
              >
                <svg className="w-8 h-8 text-terminal-accent" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
                <span className="font-bold text-xl">StockIntel</span>
              </a>
              <span className="hidden sm:inline text-terminal-textMuted">/</span>
              <span className="font-mono text-lg font-semibold text-terminal-accent">{symbol.toUpperCase()}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-terminal-textMuted">Real-time data via Yahoo Finance</span>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="border-t border-terminal-border">
            <div className="flex overflow-x-auto gap-1 pb-2" role="tablist">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                    activeTab === tab.id
                      ? "bg-terminal-accent text-terminal-bg"
                      : "text-terminal-textMuted hover:text-terminal-text hover:bg-terminal-panel"
                  )}
                  title={tab.description}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {TabComponent && <TabComponent symbol={symbol} />}
      </main>

      <Disclaimer />
    </div>
  );
}