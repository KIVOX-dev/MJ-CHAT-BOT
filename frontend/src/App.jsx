import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, Sparkles, MessageSquareCode, PlusCircle, Compass, 
  CheckCircle2, XCircle, Send, Award, Users, 
  TrendingUp, Activity, ExternalLink, ShieldCheck, AlertCircle,
  Database, Cpu, Globe, BookOpen
} from 'lucide-react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import confetti from 'canvas-confetti';

// Chat messages are rendered from LLM output, which can itself be shaped by
// scraped web content (indirect prompt injection). marked.parse() is a
// markdown-to-HTML converter, not a sanitizer, so its output must always be
// passed through DOMPurify before it reaches dangerouslySetInnerHTML.
function renderSafeMarkdown(rawText) {
  const html = marked.parse(rawText ?? '');
  return DOMPurify.sanitize(html, {
    // DOMPurify's default config already strips <script>, event handlers,
    // and javascript:/data: URLs. We additionally forbid a few tags/attrs
    // that have no legitimate use in a formatted chat bubble.
    FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['style', 'onerror', 'onload'],
  });
}

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'dashboard'
  const [query, setQuery] = useState('');
  const [sessionId, setSessionId] = useState('default');
  const [sessions, setSessions] = useState(['default']);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'ai',
      answer: "Welcome to **MJ AI**. My internal memory, math tools, and web modules are online. What would you like to investigate today?",
      source: "Core Logic (Instant Greeting)",
      confidence: "Perfect",
      latency_ms: 0,
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Metrics state
  const [metrics, setMetrics] = useState({
    total: 0,
    sources: {
      "BERT Ensemble": 0,
      "Researcher Engine": 0,
      "Ollama (Local)": 0,
      "Cloud Fallback": 0
    },
    tags: {},
    latencies: [],
    verified_memory_count: 0
  });

  const chatEndRef = useRef(null);

  // Fetch metrics & sessions
  const fetchSessionsAndMetrics = async () => {
    try {
      const resSessions = await fetch('/api/sessions');
      const dataSessions = await resSessions.json();
      if (dataSessions.sessions && dataSessions.sessions.length > 0) {
        setSessions(dataSessions.sessions);
      }
      
      const resMetrics = await fetch('/api/metrics');
      const dataMetrics = await resMetrics.json();
      setMetrics(dataMetrics);
    } catch (e) {
      console.error("Error loading backend APIs:", e);
    }
  };

  useEffect(() => {
    fetchSessionsAndMetrics();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Handle Chat Submit
  const handleSend = async (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      answer: query,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage.answer, session_id: sessionId })
      });
      const data = await response.json();

      if (data.error) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          sender: 'ai',
          answer: `⚠️ **Error**: ${data.error}`,
          source: "System Error"
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: data.msg_id || `ai-${Date.now()}`,
          sender: 'ai',
          ...data,
          timestamp: new Date().toLocaleTimeString()
        }]);
        
        // Confetti for memory checkpoint
        if (data.answer.includes("✅ Saved successfully") || data.answer.includes("remember")) {
          confetti({ particleCount: 80, spread: 60, origin: { y: 0.8 } });
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        sender: 'ai',
        answer: "⚠️ **Connection Error**: Failed to reach the MJ AI backend engine.",
        source: "Connection Module"
      }]);
    } finally {
      setIsLoading(false);
      fetchSessionsAndMetrics();
    }
  };

  const sendQuickAction = (val) => {
    setQuery(val);
    setTimeout(() => {
      const form = document.getElementById('chat-form');
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }, 50);
  };

  // Charts Config
  const doughnutData = {
    labels: Object.keys(metrics.sources),
    datasets: [{
      label: 'Acquisitions',
      data: Object.values(metrics.sources),
      backgroundColor: [
        'rgba(139, 92, 246, 0.75)', // Violet
        'rgba(6, 182, 212, 0.75)',  // Cyan
        'rgba(16, 185, 129, 0.75)', // Emerald
        'rgba(245, 158, 11, 0.75)'  // Amber
      ],
      borderColor: [
        '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'
      ],
      borderWidth: 1,
    }]
  };

  const lineData = {
    labels: metrics.latencies.map((_, i) => `Query ${i + 1}`),
    datasets: [{
      label: 'Engine Latency (ms)',
      data: metrics.latencies,
      fill: true,
      backgroundColor: 'rgba(6, 182, 212, 0.1)',
      borderColor: '#06b6d4',
      pointBackgroundColor: '#06b6d4',
      tension: 0.4
    }]
  };

  return (
    <div className="app-container">
      
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <div className="logo-area">
            <div className="logo-icon-box">
              <Brain style={{ width: '20px', height: '20px', color: 'white' }} />
            </div>
            <div>
              <h1 className="logo-text-title">MJ AI</h1>
              <p className="logo-text-subtitle">Autonomous Core</p>
            </div>
          </div>

          <div className="sidebar-section">
            <span className="section-label">Navigation</span>
            <div className="nav-links">
              <button 
                onClick={() => setActiveTab('chat')}
                className={`nav-btn ${activeTab === 'chat' ? 'active-chat' : ''}`}
              >
                <MessageSquareCode style={{ width: '16px', height: '16px' }} />
                <span>Core Interface</span>
              </button>
              <button 
                onClick={() => setActiveTab('dashboard')}
                className={`nav-btn ${activeTab === 'dashboard' ? 'active-dash' : ''}`}
              >
                <TrendingUp style={{ width: '16px', height: '16px' }} />
                <span>Intelligence Deck</span>
              </button>
            </div>
          </div>

          <div className="sidebar-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span className="section-label" style={{ margin: 0 }}>Research Sessions</span>
              <button 
                onClick={() => {
                  const newSess = `session-${Date.now()}`;
                  setSessions(prev => [...prev, newSess]);
                  setSessionId(newSess);
                  setMessages([{
                    id: `welcome-${Date.now()}`,
                    sender: 'ai',
                    answer: `New research workspace **${newSess}** initialized. Send a query to start compiling facts!`,
                    source: "Core Logic",
                    confidence: "Perfect"
                  }]);
                }}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
                title="New Session"
              >
                <PlusCircle style={{ width: '16px', height: '16px' }} />
              </button>
            </div>
            <div className="session-box">
              {sessions.map(s => (
                <button 
                  key={s}
                  onClick={() => {
                    setSessionId(s);
                    setMessages([{
                      id: `welcome-${Date.now()}`,
                      sender: 'ai',
                      answer: `Switched context to **${s}**. Ready for research.`,
                      source: "Core Logic"
                    }]);
                  }}
                  className={`session-btn ${sessionId === s ? 'active' : ''}`}
                >
                  🚀 {s}
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <span className="section-label">Connected Engines</span>
            <ul className="module-list">
              <li className="module-item"><Database style={{ width: '14px', height: '14px', color: '#c084fc' }} /> SymPy Math Core</li>
              <li className="module-item"><Cpu style={{ width: '14px', height: '14px', color: '#22d3ee' }} /> PyTorch Local Classifier</li>
              <li className="module-item"><Globe style={{ width: '14px', height: '14px', color: '#34d399' }} /> DuckDuckGo Scraper</li>
            </ul>
          </div>
        </div>

        <div className="sidebar-profile">
          <div className="profile-avatar">A</div>
          <div>
            <h4 className="profile-name">REM Administrator</h4>
            <p className="profile-role">Security Scope: Active</p>
          </div>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <main className="main-workspace">
        
        {/* Glow Accent Circles in Background (visual branding) */}
        <div style={{ position: 'absolute', top: 0, right: 0, width: '400px', height: '400px', background: 'radial-gradient(circle, rgba(139, 92, 246, 0.08) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />
        <div style={{ position: 'absolute', bottom: '-80px', left: '-80px', width: '400px', height: '400px', background: 'radial-gradient(circle, rgba(6, 182, 212, 0.05) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />

        <AnimatePresence mode="wait">
          {activeTab === 'chat' ? (
            <motion.div 
              key="chat-view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="chat-container"
              style={{ zIndex: 1 }}
            >
              {/* Header Banner */}
              <div className="header-banner">
                <div className="header-title-box">
                  <div className="workspace-badge-pill">
                    <span className="pulse-indicator" /> Active Workspace
                  </div>
                  <h2 className="header-title">
                    Research Workspace <span style={{ color: '#22d3ee', fontFamily: 'monospace' }}>#{sessionId}</span>
                  </h2>
                </div>

                <div className="header-stat-bar">
                  <div className="stat-tile">
                    <p className="stat-tile-label">Insights</p>
                    <p className="stat-tile-value violet">{metrics.total}</p>
                  </div>
                  <div className="stat-tile">
                    <p className="stat-tile-label">Verified</p>
                    <p className="stat-tile-value cyan">{metrics.verified_memory_count}</p>
                  </div>
                  <div className="stat-tile">
                    <p className="stat-tile-label">Engine</p>
                    <p className="stat-tile-value green">
                      <ShieldCheck style={{ width: '14px', height: '14px' }} /> Ollama Ready
                    </p>
                  </div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="message-stream">
                
                {/* Hero Promotion Banner */}
                <motion.div 
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1, duration: 0.4 }}
                  className="hero-banner"
                >
                  <div className="hero-tagline">
                    <Sparkles className="animate-spin-slow" style={{ width: '16px', height: '16px', color: '#22d3ee' }} />
                    <span className="hero-tag-text">MJ Intelligence Core v2.4</span>
                  </div>
                  
                  <h1 className="hero-title gradient-text">
                    Empowering Autonomous Knowledge & Reasoning
                  </h1>
                  <p className="hero-description">
                    MJ AI combines PyTorch classifiers, high-performance web scrapers, and dynamic vector context memories to guide reasoning logic. Build insights, solve math, or run detailed security reviews.
                  </p>
                  
                  <div className="hero-btn-row">
                    <button 
                      onClick={() => sendQuickAction("Run a full security audit scanning configurations")}
                      className="btn-primary"
                    >
                      <ShieldCheck style={{ width: '15px', height: '15px' }} /> Run RedSage Scan
                    </button>
                    <button 
                      onClick={() => sendQuickAction("Evaluate equation: solve for x: x^2 + 5x + 6 = 0")}
                      className="btn-secondary"
                    >
                      <Cpu style={{ width: '15px', height: '15px' }} /> Solve Math Equation
                    </button>
                  </div>
                </motion.div>

                {/* Messages mapping */}
                {messages.map((msg) => (
                  <motion.div 
                    key={msg.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`chat-bubble-row ${msg.sender === 'user' ? 'user-row' : ''}`}
                  >
                    {msg.sender === 'ai' && (
                      <div className="bubble-avatar ai-avatar">
                        <Brain style={{ width: '18px', height: '18px', color: 'white' }} />
                      </div>
                    )}
                    
                    <div className="message-bubble">
                      <div 
                        className="markdown-content" 
                        dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(msg.answer) }}
                      />

                      {msg.sender === 'ai' && (msg.source || msg.confidence) && (
                        <div className="message-meta-footer">
                          {msg.source && (
                            <span className="meta-item">
                              <Compass style={{ width: '12px', height: '12px', color: '#22d3ee' }} />
                              Source: <strong>{msg.source}</strong>
                            </span>
                          )}
                          {msg.confidence && (
                            <span className="meta-item">
                              <Award style={{ width: '12px', height: '12px', color: '#a78bfa' }} />
                              Confidence: <strong>{msg.confidence}</strong>
                            </span>
                          )}
                          {msg.latency_ms > 0 && (
                            <span style={{ fontFamily: 'monospace' }}>
                              {msg.latency_ms}ms
                            </span>
                          )}
                          {msg.report_url && (
                            <a 
                              href={msg.report_url} 
                              target="_blank" 
                              rel="noreferrer"
                              className="badge-link"
                            >
                              <ExternalLink style={{ width: '10px', height: '10px' }} /> View Report
                            </a>
                          )}
                        </div>
                      )}
                    </div>

                    {msg.sender === 'user' && (
                      <div className="bubble-avatar user-avatar">U</div>
                    )}
                  </motion.div>
                ))}

                {isLoading && (
                  <div className="chat-bubble-row">
                    <div className="bubble-avatar ai-avatar animate-pulse">
                      <Brain style={{ width: '18px', height: '18px', color: 'white' }} />
                    </div>
                    <div className="message-bubble" style={{ background: 'rgba(20, 20, 30, 0.65)', border: '1px solid var(--border-glass)', borderTopLeftRadius: 0, padding: '12px 18px', display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#a78bfa', display: 'inline-block', animation: 'bounce 1s infinite alternate' }} />
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#a78bfa', display: 'inline-block', animation: 'bounce 1s infinite alternate 0.2s' }} />
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#a78bfa', display: 'inline-block', animation: 'bounce 1s infinite alternate 0.4s' }} />
                    </div>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input Container */}
              <div className="chat-input-panel">
                <div className="quick-action-pill-row">
                  <button 
                    onClick={() => sendQuickAction("confirm")}
                    className="action-pill confirm"
                  >
                    <CheckCircle2 style={{ width: '14px', height: '14px' }} /> Confirm memory point
                  </button>
                  <button 
                    onClick={() => sendQuickAction("no")}
                    className="action-pill reject"
                  >
                    <XCircle style={{ width: '14px', height: '14px' }} /> Reject memory point
                  </button>
                  <button 
                    onClick={() => sendQuickAction("summarize session")}
                    className="action-pill normal"
                  >
                    <BookOpen style={{ width: '14px', height: '14px', color: '#a78bfa' }} /> Summarize current workspace
                  </button>
                </div>

                <form id="chat-form" onSubmit={handleSend} className="input-form-wrapper">
                  <input 
                    type="text" 
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Message MJ AI or evaluate a math equation..."
                    className="input-field-core"
                  />
                  <button 
                    type="submit" 
                    disabled={isLoading || !query.trim()}
                    className="send-btn-circle"
                  >
                    <Send style={{ width: '16px', height: '16px' }} />
                  </button>
                </form>
              </div>
            </motion.div>
          ) : (
            <motion.div 
              key="dash-view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="dashboard-viewport"
              style={{ zIndex: 1 }}
            >
              {/* Dashboard Crowdfund Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '24px', borderBottom: '1px solid var(--border-glass)' }}>
                <div>
                  <h2 className="hero-title gradient-text" style={{ margin: 0, fontSize: '1.85rem' }}>Intelligence Deck</h2>
                  <p className="hero-description" style={{ margin: '4px 0 0 0', fontSize: '0.8rem' }}>Live monitoring metrics of REM memory networks</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', background: 'rgba(0, 0, 0, 0.04)', border: '1px solid var(--border-glass)', borderRadius: '12px', fontSize: '0.75rem', color: '#475569' }}>
                  <Activity className="animate-pulse" style={{ width: '14px', height: '14px', color: '#22d3ee' }} /> Live updates from memory.json
                </div>
              </div>

              {/* Dynamic Crowdfunding layout metrics */}
              <div className="metrics-grid">
                
                {/* Vector memory metric card */}
                <motion.div whileHover={{ y: -4 }} className="campaign-metric-card">
                  <div className="campaign-card-header">
                    <span className="campaign-card-label">Vector Memories</span>
                    <Users style={{ width: '16px', height: '16px', color: '#a78bfa' }} />
                  </div>
                  <div>
                    <h3 className="campaign-card-value">{metrics.total}</h3>
                    <p className="campaign-card-desc">Acquired memory records</p>
                  </div>
                  
                  <div className="progress-track-wrapper">
                    <div className="progress-labels-box">
                      <span>PROGRESS TO BASELINE</span>
                      <span style={{ color: '#a78bfa' }}>{Math.min(100, Math.round((metrics.total/50)*100))}%</span>
                    </div>
                    <div className="progress-bar-rail">
                      <div 
                        className="progress-bar-track-filled violet" 
                        style={{ width: `${Math.min(100, Math.round((metrics.total/50)*100))}%` }} 
                      />
                    </div>
                  </div>
                </motion.div>

                {/* Verified facts metric card */}
                <motion.div whileHover={{ y: -4 }} className="campaign-metric-card">
                  <div className="campaign-card-header">
                    <span className="campaign-card-label">Verified Metrics</span>
                    <CheckCircle2 style={{ width: '16px', height: '16px', color: '#22d3ee' }} />
                  </div>
                  <div>
                    <h3 className="campaign-card-value">{metrics.verified_memory_count}</h3>
                    <p className="campaign-card-desc">Persistent semantic checkpoints</p>
                  </div>
                  
                  <div className="progress-track-wrapper">
                    <div className="progress-labels-box">
                      <span>VERIFICATION RATE</span>
                      <span style={{ color: '#22d3ee' }}>
                        {metrics.total > 0 ? Math.round((metrics.verified_memory_count / metrics.total) * 100) : 0}%
                      </span>
                    </div>
                    <div className="progress-bar-rail">
                      <div 
                        className="progress-bar-track-filled cyan" 
                        style={{ width: `${metrics.total > 0 ? Math.round((metrics.verified_memory_count / metrics.total) * 100) : 0}%` }} 
                      />
                    </div>
                  </div>
                </motion.div>

                {/* Sub-Engines Metric card */}
                <motion.div whileHover={{ y: -4 }} className="campaign-metric-card">
                  <div className="campaign-card-header">
                    <span className="campaign-card-label">Sub-Engines Engaged</span>
                    <Cpu style={{ width: '16px', height: '16px', color: '#34d399' }} />
                  </div>
                  <div>
                    <h3 className="campaign-card-value">4 Active</h3>
                    <p className="campaign-card-desc">Classification & scraping cores online</p>
                  </div>
                  
                  <div className="progress-track-wrapper">
                    <div className="progress-labels-box">
                      <span>CORE HEALTH STATUS</span>
                      <span style={{ color: '#34d399' }}>100% Online</span>
                    </div>
                    <div className="progress-bar-rail">
                      <div 
                        className="progress-bar-track-filled green" 
                        style={{ width: '100%' }} 
                      />
                    </div>
                  </div>
                </motion.div>

              </div>

              {/* Graphical sections */}
              <div className="charts-row-container">
                
                {/* Donut chart */}
                <div className="chart-card-box">
                  <h3 className="chart-card-title">Acquisition Channels</h3>
                  <div className="chart-render-frame">
                    <Doughnut 
                      data={doughnutData} 
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'bottom',
                            labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 10 } }
                          }
                        }
                      }} 
                    />
                  </div>
                </div>

                {/* Line Latency Chart */}
                <div className="chart-card-box">
                  <h3 className="chart-card-title">Engine Latency Stream</h3>
                  <div className="chart-render-frame">
                    {metrics.latencies.length > 0 ? (
                      <Line 
                        data={lineData} 
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          scales: {
                            y: { grid: { color: 'rgba(0, 0, 0, 0.05)' }, ticks: { color: '#64748b', font: { size: 9 } } },
                            x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 9 } } }
                          },
                          plugins: {
                            legend: { display: false }
                          }
                        }}
                      />
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', color: '#64748b', fontSize: '0.8rem' }}>
                        <AlertCircle style={{ width: '32px', height: '32px', color: '#475569' }} />
                        <span>No query records captured yet in this workspace.</span>
                      </div>
                    )}
                  </div>
                </div>

              </div>

            </motion.div>
          )}
        </AnimatePresence>

      </main>

    </div>
  );
}
