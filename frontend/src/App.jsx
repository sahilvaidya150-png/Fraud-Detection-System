import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "./api/axios.js";
import Login from "./pages/Login.jsx";

const NAV_ITEMS = [
  ["overview", "Overview", "◫"],
  ["predict", "Fraud prediction", "⌁"],
  ["transactions", "Transactions", "▤"],
  ["monitoring", "Monitoring", "◉"],
  ["performance", "Model performance", "▥"],
  ["model", "Model management", "◇"],
];

const INITIAL_FORM = {
  step: "400",
  type: "CASH_OUT",
  amount: "150000",
  oldbalanceOrg: "200000",
  newbalanceOrig: "50000",
  oldbalanceDest: "0",
  newbalanceDest: "0",
};

function ErrorState({ message, onRetry }) {
  return (
    <div className="state-card error-state" role="alert">
      <strong>Couldn’t load this data</strong>
      <span>{message}</span>
      {onRetry && <button className="button button-quiet" onClick={onRetry}>Try again</button>}
    </div>
  );
}

function MetricCard({ label, value, note, accent }) {
  return (
    <article className="metric-card">
      <div className="metric-label">{label}<span className={`metric-dot ${accent || ""}`} /></div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </article>
  );
}

function DataTable({ rows, loading }) {
  if (loading) return <div className="state-card">Loading transaction records…</div>;
  if (!rows.length) return <div className="state-card">No transaction records are available.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Transaction</th><th>Type</th><th>Amount</th><th>Step</th><th>Label / score</th></tr></thead>
        <tbody>{rows.map((row) => (
          <tr key={row.transaction_id}>
            <td className="mono">{row.transaction_id}</td>
            <td><span className="type-pill">{row.type}</span></td>
            <td>${Number(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td>{row.step ?? "—"}</td>
            <td><span className={`status-pill ${row.is_fraud ? "status-risk" : "status-safe"}`}>{row.record_source === "prediction" ? (row.is_fraud ? "Flagged" : "Not flagged") : (row.is_fraud ? "Fraud" : "Legitimate")}</span>{row.fraud_probability != null && <span className="table-probability"> {(row.fraud_probability * 100).toFixed(1)}%</span>}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function MetricBars({ metrics }) {
  const items = [
    ["Precision", metrics.precision],
    ["Recall", metrics.recall],
    ["F1 score", metrics.f1],
    ["ROC AUC", metrics.roc_auc],
    ["Average precision", metrics.average_precision],
  ];
  return <div className="metric-bars">{items.map(([label, value]) => (
    <div className="bar-row" key={label}>
      <span>{label}</span>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(0, Math.min(1, Number(value) || 0)) * 100}%` }} /></div>
      <strong>{Number(value || 0).toFixed(3)}</strong>
    </div>
  ))}</div>;
}

function App() {
  const [authUser, setAuthUser] = useState("");
  const [authChecking, setAuthChecking] = useState(true);
  const [authError, setAuthError] = useState("");
  const [page, setPage] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [storedPredictions, setStoredPredictions] = useState([]);
  const [transactionTotal, setTransactionTotal] = useState(0);
  const [monitoring, setMonitoring] = useState(null);
  const [model, setModel] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(INITIAL_FORM);
  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [overviewData, transactionData, monitoringData, modelData] = await Promise.all([
        apiRequest("/api/analytics/overview"),
        apiRequest("/api/transactions/?limit=8"),
        apiRequest("/api/monitoring/"),
        apiRequest("/api/model/"),
      ]);
      setOverview(overviewData);
      setTransactions(transactionData.items || []);
      setStoredPredictions(transactionData.stored_predictions || []);
      setTransactionTotal(transactionData.total || 0);
      setMonitoring(monitoringData);
      setModel(modelData);
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkSession = useCallback(async () => {
    setAuthChecking(true);
    setAuthError("");
    try {
      const session = await apiRequest("/api/auth/session");
      setAuthUser(session.authenticated ? session.username : "");
    } catch (error) {
      setAuthUser("");
      setAuthError(error.message);
    } finally {
      setAuthChecking(false);
    }
  }, []);

  useEffect(() => { checkSession(); }, [checkSession]);
  useEffect(() => { if (authUser) refresh(); }, [authUser, refresh]);

  async function submitPrediction(event) {
    event.preventDefault();
    setPredicting(true);
    setPredictionError("");
    setPrediction(null);
    try {
      const body = Object.fromEntries(Object.entries(form).map(([key, value]) => (
        [key, key === "type" ? value : Number(value)]
      )));
      const result = await apiRequest("/api/predictions/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPrediction(result);
      await refresh();
    } catch (error) {
      setPredictionError(error.message);
    } finally {
      setPredicting(false);
    }
  }

  async function logout() {
    try {
      await apiRequest("/api/auth/logout", { method: "POST" });
      setAuthUser("");
      setPage("overview");
      setOverview(null);
      setTransactions([]);
      setStoredPredictions([]);
      setMonitoring(null);
      setModel(null);
    } catch (error) {
      setLoadError(error.message);
    }
  }

  if (authChecking) {
    return <main className="login-page"><div className="login-loading"><span className="connection-dot" /> Checking secure session…</div></main>;
  }
  if (!authUser) {
    return <Login onLogin={setAuthUser} onRetry={checkSession} serviceError={authError} />;
  }

  const raw = overview?.full_dataset;
  const evaluation = overview?.evaluation;
  const scores = evaluation?.metrics;
  const pageTitle = NAV_ITEMS.find(([id]) => id === page)?.[1] || "Overview";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setPage("overview"); }}>
          <span className="brand-mark">S</span>
          <span><strong>SENTINEL</strong><small>RISK INTELLIGENCE</small></span>
        </a>
        <div className="nav-caption">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV_ITEMS.map(([id, label, icon]) => (
            <button key={id} className={`nav-link ${page === id ? "active" : ""}`} onClick={() => setPage(id)} aria-current={page === id ? "page" : undefined}>
              <span className="nav-icon" aria-hidden="true">{icon}</span>{label}
              {id === "monitoring" && monitoring?.flagged_predictions > 0 && <span className="nav-count">{monitoring.flagged_predictions}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection"><span className={`connection-dot ${loadError ? "offline" : ""}`} /><span>{loadError ? "API unavailable" : "Risk engine connected"}</span></div>
          <div className="user-row"><span className="avatar">{authUser.slice(0, 2).toUpperCase()}</span><span><strong>{authUser}</strong><small>Authenticated analyst</small></span><button aria-label="Sign out" className="signout-button" onClick={logout} title="Sign out">↗</button></div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div><div className="eyebrow">FRAUD INTELLIGENCE / {page.toUpperCase()}</div><h1>{pageTitle}</h1></div>
          <div className="topbar-actions">
            <span className="environment-pill"><span className="connection-dot" /> LOCAL ENVIRONMENT</span>
            <button className="button button-quiet" onClick={refresh} disabled={loading}>↻ <span>Refresh</span></button>
          </div>
        </header>

        {loadError && <ErrorState message={loadError} onRetry={refresh} />}
        {page === "overview" && (
          <>
            <section className="welcome-row">
              <div><h2>Good day, analyst</h2><p>PaySim fraud model · evaluation and prediction workspace</p></div>
              <div className="model-chip"><span className="connection-dot" />{model?.status === "loaded" ? "MODEL ACTIVE" : "MODEL STATUS UNKNOWN"}</div>
            </section>
            <section className="metric-grid">
              <MetricCard label="RAW TRANSACTIONS" value={raw?.rows?.toLocaleString() || "—"} note="Full PaySim dataset" />
              <MetricCard label="LABELLED FRAUD" value={raw?.class_counts?.["1"]?.toLocaleString() || "—"} note={`${((raw?.fraud_rate || 0) * 100).toFixed(3)}% of raw records`} accent="orange" />
              <MetricCard label="MODEL RECALL" value={scores ? `${(scores.recall * 100).toFixed(1)}%` : "—"} note="Stratified holdout · threshold 0.50" accent="cyan" />
              <MetricCard label="SAVED SCORES" value={monitoring?.total_predictions?.toLocaleString() || "0"} note="Predictions persisted locally" accent="green" />
            </section>
            <section className="content-grid">
              <article className="panel">
                <div className="panel-heading"><div><span className="panel-kicker">MODEL EVALUATION</span><h3>Holdout performance</h3></div><span className="subtle-tag">SAMPLED COHORT</span></div>
                {scores ? <MetricBars metrics={scores} /> : <div className="state-card">Evaluation metrics are not available.</div>}
                <p className="footnote">{evaluation?.caveat || "Metrics are sourced from the saved model evaluation report."}</p>
              </article>
              <article className="panel">
                <div className="panel-heading"><div><span className="panel-kicker">DATASET PROFILE</span><h3>Transaction mix</h3></div><span className="subtle-tag">{raw?.rows?.toLocaleString() || "—"} ROWS</span></div>
                <div className="type-bars">
                  {Object.entries(raw?.transaction_type_counts || {}).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                    const max = Math.max(...Object.values(raw.transaction_type_counts));
                    return <div className="type-row" key={type}><span>{type.replace("_", " ")}</span><div className="bar-track"><div className="bar-fill" style={{ width: `${(count / max) * 100}%` }} /></div><strong>{count.toLocaleString()}</strong></div>;
                  })}
                </div>
              </article>
            </section>
            <section className="panel">
              <div className="panel-heading"><div><span className="panel-kicker">PROCESSED DATASET</span><h3>Transaction sample</h3></div><button className="text-button" onClick={() => setPage("transactions")}>View all →</button></div>
              <DataTable rows={transactions.slice(0, 5)} loading={loading} />
              <p className="footnote">Observed labels from <span className="mono">{overview?.training_dataset || "the processed training sample"}</span>; this is not live traffic.</p>
            </section>
          </>
        )}

        {page === "predict" && (
          <section className="form-layout">
            <article className="panel">
              <div className="panel-heading"><div><span className="panel-kicker">SINGLE TRANSACTION</span><h3>Score transaction risk</h3></div><span className="subtle-tag">REAL MODEL</span></div>
              <p className="panel-copy">Enter PaySim transaction values. The API applies the exact saved preprocessing pipeline used during training.</p>
              <form className="prediction-form" onSubmit={submitPrediction}>
                <label>Transaction type<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>{["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"].map((type) => <option key={type}>{type}</option>)}</select></label>
                <label>Amount<input required type="number" min="0" step="any" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
                <label>Time step<input required type="number" min="0" step="1" value={form.step} onChange={(e) => setForm({ ...form, step: e.target.value })} /></label>
                <label>Origin balance before<input required type="number" min="0" step="any" value={form.oldbalanceOrg} onChange={(e) => setForm({ ...form, oldbalanceOrg: e.target.value })} /></label>
                <label>Origin balance after<input required type="number" min="0" step="any" value={form.newbalanceOrig} onChange={(e) => setForm({ ...form, newbalanceOrig: e.target.value })} /></label>
                <label>Destination balance before<input required type="number" min="0" step="any" value={form.oldbalanceDest} onChange={(e) => setForm({ ...form, oldbalanceDest: e.target.value })} /></label>
                <label>Destination balance after<input required type="number" min="0" step="any" value={form.newbalanceDest} onChange={(e) => setForm({ ...form, newbalanceDest: e.target.value })} /></label>
                <button className="button button-primary" type="submit" disabled={predicting}>{predicting ? "Scoring…" : "Run fraud assessment"}</button>
              </form>
              {predictionError && <p className="inline-error" role="alert">{predictionError}</p>}
            </article>
            <article className="panel result-panel">
              <span className="panel-kicker">ASSESSMENT RESULT</span>
              {prediction ? (
                <>
                  <div className={`result-icon ${prediction.is_fraud ? "risk" : ""}`}>{prediction.is_fraud ? "!" : "✓"}</div>
                  <h2>{prediction.is_fraud ? "High risk" : "Low risk"}</h2>
                  <p>Fraud probability</p><div className="probability">{(prediction.fraud_probability * 100).toFixed(2)}<small>%</small></div>
                  <div className="threshold-note">Decision threshold {(prediction.threshold * 100).toFixed(0)}% · saved as transaction #{prediction.transaction_id}</div>
                </>
              ) : <div className="empty-result"><span>◎</span><strong>Awaiting transaction</strong><p>Submit the transaction details to receive a scored result.</p></div>}
            </article>
          </section>
        )}

        {page === "transactions" && (
          <section className="panel">
            <div className="panel-heading"><div><span className="panel-kicker">DATA SOURCE: {overview?.training_dataset || "FRAUD_SAMPLE"}</span><h3>Processed transactions</h3></div><span className="subtle-tag">{transactionTotal.toLocaleString()} RECORDS</span></div>
            <p className="panel-copy">Dataset rows retain observed labels; submitted model predictions are also included and identified separately.</p>
            <DataTable rows={[...storedPredictions, ...transactions]} loading={loading} />
          </section>
        )}

        {page === "monitoring" && (
          <section className="content-grid">
            <article className="panel"><span className="panel-kicker">LOCAL SCORING ACTIVITY</span><h3>Prediction activity</h3>
              {monitoring ? <div className="activity-stats"><div><strong>{monitoring.total_predictions}</strong><span>Transactions scored</span></div><div><strong>{monitoring.flagged_predictions}</strong><span>Above decision threshold</span></div></div> : <div className="state-card">Monitoring data is not available.</div>}
              <div className="empty-state-note">Activity reflects requests scored and stored by this local application; it is not a live feed.</div>
              {monitoring?.recent_predictions?.length > 0 && <div className="monitoring-table"><div className="panel-kicker">RECENT MODEL SCORES</div><DataTable rows={monitoring.recent_predictions} loading={false} /> </div>}
            </article>
            <article className="panel"><span className="panel-kicker">DRIFT MONITORING</span><h3>Data drift</h3>
              <div className="drift-state"><span className="drift-mark">—</span><div><strong>Not configured</strong><p>{monitoring?.drift_note || "A labelled live reference batch is required before drift can be estimated."}</p></div></div>
            </article>
          </section>
        )}

        {page === "performance" && (
          <section className="content-grid">
            <article className="panel"><div className="panel-heading"><div><span className="panel-kicker">STRATIFIED HOLDOUT</span><h3>Classification metrics</h3></div><span className="subtle-tag">THRESHOLD {overview?.threshold ?? "—"}</span></div>
              {scores ? <MetricBars metrics={scores} /> : <div className="state-card">No saved model evaluation is available.</div>}
              <p className="footnote">{evaluation?.caveat}</p>
            </article>
            <article className="panel"><span className="panel-kicker">CONFUSION MATRIX</span><h3>Actual × predicted</h3>
              {scores?.confusion_matrix ? <div className="confusion-grid"><span /><span>Predicted 0</span><span>Predicted 1</span><strong>Actual 0</strong><b>{scores.confusion_matrix[0][0].toLocaleString()}</b><b>{scores.confusion_matrix[0][1].toLocaleString()}</b><strong>Actual 1</strong><b>{scores.confusion_matrix[1][0].toLocaleString()}</b><b>{scores.confusion_matrix[1][1].toLocaleString()}</b></div> : <div className="state-card">Confusion matrix is unavailable.</div>}
            </article>
          </section>
        )}

        {page === "model" && (
          <section className="panel model-panel">
            <div className="panel-heading"><div><span className="panel-kicker">MODEL REGISTRY</span><h3>Production artifact</h3></div><span className={`status-pill ${model?.status === "loaded" ? "status-safe" : "status-risk"}`}>{model?.status || "Unavailable"}</span></div>
            {model ? <dl className="model-details"><dt>Estimator</dt><dd>{model.model}</dd><dt>Feature set</dt><dd>{model.features.join(", ")}</dd><dt>Decision threshold</dt><dd>{model.threshold}</dd><dt>Trained at</dt><dd>{new Date(model.created_at).toLocaleString()}</dd><dt>scikit-learn</dt><dd>{model.scikit_learn_version}</dd></dl> : <ErrorState message={loadError || "Model artifact details are unavailable."} />}
            <div className="empty-state-note">The model artifact is loaded from the project’s models/production directory. Retraining is performed with <code>python -m ml.models.train</code>.</div>
          </section>
        )}
        <footer className="footer-note"><span>PAYMENTS RISK PLATFORM</span><span>Data & model metrics shown with recorded provenance</span></footer>
      </main>
    </div>
  );
}

export default App;