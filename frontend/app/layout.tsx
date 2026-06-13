import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';

export const metadata: Metadata = {
  title: 'EAIOC | Enterprise AI Operations Center',
  description: 'Multi-Agent Orchestration, Secure RAG, Multimodal AI, Voice Agent, and Edge LLM Deployment',
  keywords: 'AI, MLOps, LangGraph, RAG, enterprise, orchestration, edge deployment',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="dashboard-root">
          <Sidebar />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Topbar />
            <main className="page-content animate-fade-in">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
