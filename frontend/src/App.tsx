import { useState, useEffect, useRef, useCallback } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import "./index.css";
import { API, fmtINR, fmtPct, fmtDate, CATEGORY_COLORS, ACCOUNT_ICONS } from "./utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Summary {
  net_worth:             { net_worth: number; assets: number; liabilities: number };
  total_balance:         { total_balance: number };
  spending_by_category:  { categories: Record<string, number>; total: number };
  monthly_trend:         { month: string; income: number; spending: number; savings: number }[];
  savings_rate:          { rate_percent: number; savings: number; income: number };
  liabilities:           { liabilities: { name: string; type: string; balance: number }[]; total: number };
}

interface Anomaly {
  id: number;
  transaction: { merchant: string; amount: number; date: string; category: string };
  reason_code: string;
  severity: string;
  detail: string;
  explanation: string;
}

interface ChatMessage {
  role: "user" | "bot";
  content: string;
  tool_calls?: { name: string; arguments: Record<string, unknown>; result: unknown }[];
}

interface GoalResult {
  id: number;
  name: string;
  plan: {
    required_monthly: number;
    avg_monthly_surplus: number;
    shortfall: number;
    feasible: boolean;
    formatted_required: string;
    formatted_surplus: string;
  };
  summary: string;
}

interface FileState {
  name: string;
  status: "pending" | "loading" | "done" | "error";
  detail: string;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="card stat-card">
      <div className="skeleton skel-label" />
      <div className="skeleton skel-value" style={{ marginTop: 10 }} />
      <div className="skeleton skel-label" style={{ width: 60, marginTop: 8 }} />
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, colorClass = "" }: {
  label: string; value: string; sub?: string; colorClass?: string;
}) {
  return (
    <div className="card stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${colorClass}`}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

// ── Upload Zone ───────────────────────────────────────────────────────────────

function UploadSection({ onDataLoaded }: { onDataLoaded: () => void }) {
  const [files, setFiles]         = useState<FileState[]>([]);
  const [dragging, setDragging]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const inputRef                  = useRef<HTMLInputElement>(null);

  const ingestFiles = async (raw: File[]) => {
    if (!raw.length) return;
    const newFiles: FileState[] = raw.map(f => ({ name: f.name, status: "pending", detail: "" }));
    setFiles(prev => [...prev, ...newFiles]);

    const formData = new FormData();
    raw.forEach(f => formData.append("files", f));

    // Mark all as loading
    setFiles(prev => prev.map(f =>
      raw.find(r => r.name === f.name) ? { ...f, status: "loading" } : f
    ));

    try {
      const res  = await fetch(`${API}/api/ingest`, { method: "POST", body: formData });
      const data = await res.json();
      setFiles(prev => prev.map(f => {
        const result = data.results?.find((r: any) => r.file === f.name);
        if (result) {
          if (result.error) return { ...f, status: "error", detail: result.error };
          return { ...f, status: "done", detail: `${result.transactions} txns` };
        }
        return f;
      }));
      onDataLoaded();
    } catch (e: any) {
      setFiles(prev => prev.map(f =>
        raw.find(r => r.name === f.name) ? { ...f, status: "error", detail: e.message } : f
      ));
    }
  };

  const loadDemo = async () => {
    setLoading(true);
    const demoFiles = [
      "bank_statement_1.png","bank_statement_2.png",
      "upi_screenshot.png","credit_card_statement.pdf","loan_insurance.pdf"
    ].map(n => ({ name: n, status: "loading" as const, detail: "" }));
    setFiles(demoFiles);
    try {
      const res  = await fetch(`${API}/api/demo/load`, { method: "POST" });
      const data = await res.json();
      setFiles(demoFiles.map(f => {
        const r = data.results?.find((x: any) => x.file === f.name);
        if (!r) return { ...f, status: "done", detail: "cached" };
        if (r.error) return { ...f, status: "error", detail: r.error };
        return { ...f, status: "done", detail: `${r.transactions} txns` };
      }));
      onDataLoaded();
    } catch (e: any) {
      setFiles(demoFiles.map(f => ({ ...f, status: "error", detail: e.message })));
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    ingestFiles(Array.from(e.dataTransfer.files));
  };

  return (
    <section className="section">
      <h2 className="section-title">Upload Financial Documents</h2>
      <div
        className={`upload-zone ${dragging ? "drag-over" : ""}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div className="upload-icon">📂</div>
        <div className="upload-title">Drop bank statements, UPI screenshots, PDFs here</div>
        <div className="upload-sub">Supports PNG, JPG, PDF · Processed locally on your device</div>
        <input
          ref={inputRef} type="file" multiple
          accept=".png,.jpg,.jpeg,.pdf"
          style={{ display: "none" }}
          onChange={e => e.target.files && ingestFiles(Array.from(e.target.files))}
        />
      </div>
      <div className="upload-actions">
        <button className="btn btn-primary" onClick={loadDemo} disabled={loading}>
          {loading ? "⏳ Loading…" : "✨ Load Demo Files"}
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => setFiles([])}>Clear</button>
      </div>
      {files.length > 0 && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={i} className="file-item">
              <span style={{ fontSize: 18 }}>
                {f.name.endsWith(".pdf") ? "📄" : "🖼️"}
              </span>
              <span className="file-name">{f.name}</span>
              {f.status === "loading" && (
                <div style={{ flex:1, maxWidth: 120 }}>
                  <div className="progress-bar"><div className="progress-fill" style={{ width: "60%" }} /></div>
                </div>
              )}
              <span className={`file-state state-${f.status}`}>
                {f.status === "loading" ? "Extracting…" :
                 f.status === "done"    ? `✓ ${f.detail}` :
                 f.status === "error"   ? `✗ ${f.detail}` : "Pending"}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ── Overview ──────────────────────────────────────────────────────────────────

function Overview({ summary, loading }: { summary: Summary | null; loading: boolean }) {
  if (loading) return (
    <section className="section">
      <h2 className="section-title">Overview</h2>
      <div className="grid-4">
        {[0,1,2,3].map(i => <Skeleton key={i} />)}
      </div>
    </section>
  );

  if (!summary) return (
    <section className="section">
      <h2 className="section-title">Overview</h2>
      <div className="empty">
        <div className="empty-icon">💡</div>
        <div className="empty-title">No data yet</div>
        <div className="empty-sub">Upload documents or load demo files to see your dashboard</div>
      </div>
    </section>
  );

  const nw      = summary.net_worth;
  const sr      = summary.savings_rate;
  const balance = summary.total_balance;
  const spend   = summary.spending_by_category;

  return (
    <section className="section">
      <h2 className="section-title">Overview</h2>
      <div className="grid-4">
        <StatCard
          label="Total Balance"
          value={fmtINR(balance.total_balance)}
          sub="Bank + Wallet accounts"
          colorClass="stat-accent"
        />
        <StatCard
          label="Net Worth"
          value={fmtINR(nw.net_worth)}
          sub={`Assets ${fmtINR(nw.assets)} · Debts ${fmtINR(nw.liabilities)}`}
          colorClass={nw.net_worth >= 0 ? "stat-pos" : "stat-neg"}
        />
        <StatCard
          label="Monthly Spending"
          value={fmtINR(spend.total)}
          sub="Last 30 days (debits)"
        />
        <StatCard
          label="Savings Rate"
          value={fmtPct(sr.rate_percent)}
          sub={`Saving ${fmtINR(sr.savings)} of ${fmtINR(sr.income)}`}
          colorClass={sr.rate_percent >= 20 ? "stat-pos" : sr.rate_percent >= 10 ? "" : "stat-neg"}
        />
      </div>
    </section>
  );
}

// ── Charts ────────────────────────────────────────────────────────────────────

function Charts({ summary, loading }: { summary: Summary | null; loading: boolean }) {
  if (!summary && !loading) return null;

  const pieData = summary
    ? Object.entries(summary.spending_by_category.categories)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value }))
    : [];

  const barData = summary?.monthly_trend ?? [];

  const accounts = summary ? (() => {
    const conn = summary.net_worth;
    // Group by type using liabilities + total_balance placeholder
    return summary.liabilities.liabilities;
  })() : [];

  return (
    <section className="section">
      <h2 className="section-title">Charts & Accounts</h2>
      <div className="grid-2">
        {/* Spending donut */}
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Spending by Category</div>
          {loading ? (
            <div className="skeleton" style={{ height: 280 }} />
          ) : pieData.length === 0 ? (
            <div className="empty"><div className="empty-icon">🍩</div><div className="empty-sub">No spending data</div></div>
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={2}>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] ?? "#94A3B8"} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtINR(v)} />
                  <Legend formatter={(v) => v} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Monthly bar */}
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Monthly Trend</div>
          {loading ? (
            <div className="skeleton" style={{ height: 280 }} />
          ) : barData.length === 0 ? (
            <div className="empty"><div className="empty-icon">📊</div><div className="empty-sub">No trend data</div></div>
          ) : (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 10, right: 10, bottom: 0, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => fmtINR(v)} />
                  <Legend />
                  <Bar dataKey="income"   name="Income"   fill="#10B981" radius={[4,4,0,0]} />
                  <Bar dataKey="spending" name="Spending"  fill="#6366F1" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Accounts breakdown */}
      {summary && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Liabilities</div>
          {summary.liabilities.liabilities.length === 0 ? (
            <div className="empty"><div className="empty-sub">No liability accounts</div></div>
          ) : (
            <div className="accounts-list">
              {summary.liabilities.liabilities.map((acc, i) => (
                <div key={i} className="account-item">
                  <div className="account-info">
                    <div className={`account-icon icon-${acc.type}`}>
                      {ACCOUNT_ICONS[acc.type] ?? "💰"}
                    </div>
                    <div>
                      <div className="account-name">{acc.name}</div>
                      <div className="account-type">{acc.type}</div>
                    </div>
                  </div>
                  <div className={`account-bal ${acc.balance < 0 ? "negative" : ""}`}>
                    {fmtINR(Math.abs(acc.balance))} owed
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ── Alerts ────────────────────────────────────────────────────────────────────

function Alerts({ anomalies, loading }: { anomalies: Anomaly[]; loading: boolean }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <section className="section">
      <h2 className="section-title">
        Alerts
        {anomalies.length > 0 && (
          <span style={{ marginLeft: 10, fontSize: 14, color: "#EF4444", fontWeight: 500 }}>
            {anomalies.length} found
          </span>
        )}
      </h2>
      {loading ? (
        <div className="card">
          {[0,1].map(i => <div key={i} className="skeleton" style={{ height: 60, marginBottom: 8 }} />)}
        </div>
      ) : anomalies.length === 0 ? (
        <div className="card">
          <div className="empty">
            <div className="empty-icon">✅</div>
            <div className="empty-title">No anomalies detected</div>
            <div className="empty-sub">Load financial data to check for suspicious transactions</div>
          </div>
        </div>
      ) : (
        <div>
          {anomalies.map(a => (
            <div key={a.id} className={`card anomaly-card ${a.severity}`}>
              <div className="anomaly-header">
                <div>
                  <span className={`anomaly-badge badge-${a.severity}`}>{a.severity}</span>
                  {" "}
                  <span className={`anomaly-badge badge-${a.severity}`} style={{ marginLeft: 6 }}>
                    {a.reason_code.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="anomaly-amount">{fmtINR(a.transaction.amount)}</div>
              </div>
              <div className="anomaly-merchant">{a.transaction.merchant}</div>
              <div className="anomaly-meta">
                {fmtDate(a.transaction.date)} · {a.transaction.category}
              </div>
              <div
                className="anomaly-explanation"
                style={{ cursor: "pointer" }}
                onClick={() => setExpanded(expanded === a.id ? null : a.id)}
              >
                {a.explanation || a.detail}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ── Goal Planner ──────────────────────────────────────────────────────────────

function GoalPlanner() {
  const [name,   setName]   = useState("Bike");
  const [amount, setAmount] = useState("300000");
  const [months, setMonths] = useState("18");
  const [result, setResult] = useState<GoalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]  = useState("");

  const submit = async () => {
    setLoading(true); setError("");
    try {
      const res  = await fetch(`${API}/api/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, target_amount: Number(amount), months: Number(months) }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="section">
      <h2 className="section-title">Goal Planner</h2>
      <div className="card">
        <div className="goal-form">
          <div className="form-group">
            <label className="form-label">Goal Name</label>
            <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Bike, Vacation" />
          </div>
          <div className="form-group">
            <label className="form-label">Target Amount (₹)</label>
            <input className="form-input" type="number" value={amount} onChange={e => setAmount(e.target.value)} placeholder="300000" />
          </div>
          <div className="form-group">
            <label className="form-label">Months</label>
            <input className="form-input" type="number" value={months} onChange={e => setMonths(e.target.value)} placeholder="18" />
          </div>
          <button className="btn btn-primary" onClick={submit} disabled={loading} style={{ marginTop: 22 }}>
            {loading ? "⏳ Planning…" : "Plan Goal"}
          </button>
        </div>

        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}

        {result && (
          <div className="goal-result">
            <div className={`goal-feasible ${result.plan.feasible ? "yes" : "no"}`}>
              {result.plan.feasible ? "✅ Feasible!" : "⚠️ Challenging — but achievable with adjustments"}
            </div>
            <div className="goal-numbers">
              <div className="goal-num">
                <div className="goal-num-val">{result.plan.formatted_required}</div>
                <div className="goal-num-label">Needed/month</div>
              </div>
              <div className="goal-num">
                <div className="goal-num-val">{result.plan.formatted_surplus}</div>
                <div className="goal-num-label">Current surplus</div>
              </div>
              {!result.plan.feasible && (
                <div className="goal-num">
                  <div className="goal-num-val" style={{ color: "#EF4444" }}>{fmtINR(result.plan.shortfall)}</div>
                  <div className="goal-num-label">Monthly shortfall</div>
                </div>
              )}
            </div>
            <div className="goal-summary">{result.summary}</div>
          </div>
        )}
      </div>
    </section>
  );
}

// ── Advisor Chat ──────────────────────────────────────────────────────────────

const SUGGESTED = [
  "Can I afford a ₹3,00,000 bike in 18 months?",
  "How much did I spend on food last month?",
  "What is my net worth?",
  "What if I cut shopping by 30%?",
  "Anything suspicious in my transactions?",
];

function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: text };
    const history = messages.slice(-6).map(m => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content,
    }));

    setMessages(prev => [...prev, userMsg, { role: "bot", content: "…", tool_calls: [] }]);
    setInput("");
    setLoading(true);

    try {
      const res  = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "bot", content: data.answer, tool_calls: data.tool_calls ?? [] },
      ]);
    } catch (e: any) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "bot", content: `Error: ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [messages, loading]);

  return (
    <section className="section">
      <h2 className="section-title">Advisor Chat</h2>
      <div className="card" style={{ padding: 0 }}>
        <div className="chat-box">
          <div className="chat-messages" style={{ background: "#FAFAFA" }}>
            {messages.length === 0 && (
              <div className="empty" style={{ marginTop: 40 }}>
                <div className="empty-icon">💬</div>
                <div className="empty-title">Ask anything about your finances</div>
                <div className="empty-sub">All analysis runs locally on your device</div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i}>
                <div className={`chat-msg ${m.role} ${m.content === "…" ? "typing" : ""}`}>
                  {m.content}
                </div>
                {m.role === "bot" && (m.tool_calls?.length ?? 0) > 0 && (
                  <div className="tools-used" style={{ paddingLeft: 8 }}>
                    <button
                      className="tools-toggle"
                      onClick={() => setExpanded(expanded === i ? null : i)}
                    >
                      {expanded === i ? "▲" : "▼"} {m.tool_calls!.length} tool{m.tool_calls!.length !== 1 ? "s" : ""} used
                    </button>
                    {expanded === i && m.tool_calls!.map((tc, j) => (
                      <div key={j} className="tool-item">
                        <div className="tool-name">{tc.name}({JSON.stringify(tc.arguments)})</div>
                        <div className="tool-result">{JSON.stringify(tc.result, null, 2)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {messages.length === 0 && (
            <div style={{ padding: "8px 16px" }}>
              <div className="chips">
                {SUGGESTED.map((s, i) => (
                  <button key={i} className="chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          <div className="chat-footer">
            <textarea
              className="chat-input"
              rows={2}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask about your spending, goals, anomalies…"
              disabled={loading}
            />
            <button className="btn btn-primary" onClick={() => send(input)} disabled={loading || !input.trim()}>
              {loading ? "⏳" : "→"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [summary,   setSummary]   = useState<Summary | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [sumLoading, setSumLoading] = useState(false);
  const [anmLoading, setAnmLoading] = useState(false);
  const [backendOk,  setBackendOk]  = useState(true);
  const [resetLoading, setResetLoading] = useState(false);

  const loadSummary = useCallback(async () => {
    setSumLoading(true);
    try {
      const res  = await fetch(`${API}/api/summary`);
      const data = await res.json();
      setSummary(data);
      setBackendOk(true);
    } catch {
      setBackendOk(false);
    } finally {
      setSumLoading(false);
    }
  }, []);

  const loadAnomalies = useCallback(async () => {
    setAnmLoading(true);
    try {
      const res  = await fetch(`${API}/api/anomalies`);
      const data = await res.json();
      setAnomalies(data.anomalies ?? []);
    } catch {}
    finally { setAnmLoading(false); }
  }, []);

  const onDataLoaded = useCallback(() => {
    loadSummary();
    loadAnomalies();
  }, [loadSummary, loadAnomalies]);

  const handleReset = async () => {
    setResetLoading(true);
    try {
      await fetch(`${API}/api/reset`, { method: "POST" });
      setSummary(null);
      setAnomalies([]);
    } finally {
      setResetLoading(false);
    }
  };

  useEffect(() => { loadSummary(); loadAnomalies(); }, []);

  return (
    <>
      {/* Sticky top bar */}
      <header className="topbar">
        <span className="topbar-brand">🗺️ MoneyMap</span>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span className="topbar-note">
            <span className="topbar-dot" />
            Runs locally on your device
          </span>
          <button
            className="btn btn-outline btn-sm"
            onClick={handleReset}
            disabled={resetLoading}
            style={{ fontSize: 12 }}
          >
            {resetLoading ? "…" : "Reset DB"}
          </button>
        </div>
      </header>

      <main className="main">
        {!backendOk && (
          <div className="backend-down">
            ⚠️ Cannot connect to backend at {API}. Make sure uvicorn is running.
          </div>
        )}

        <UploadSection onDataLoaded={onDataLoaded} />
        <Overview    summary={summary} loading={sumLoading} />
        <Charts      summary={summary} loading={sumLoading} />
        <Alerts      anomalies={anomalies} loading={anmLoading} />
        <GoalPlanner />
        <Chat />
      </main>
    </>
  );
}
