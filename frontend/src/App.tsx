import './App.css'

function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="ELD Trip Planner home">
          <span className="wordmark-mark" aria-hidden="true">
            E
          </span>
          <span>ELD Trip Planner</span>
        </a>
        <span className="topbar-section">TRIP DESK</span>
      </header>

      <main className="workspace" aria-labelledby="page-title">
        <div className="section-label">
          <span className="section-dot" aria-hidden="true" />
          ROUTE PLANNING
        </div>
        <h1 id="page-title">Trip planning workspace</h1>
        <p className="workspace-copy">
          Your route, hours-of-service schedule, and daily logs will come
          together here.
        </p>
        <div className="workspace-rule" />
        <p className="workspace-state" role="status">
          Planning tools are being set up.
        </p>
      </main>
    </div>
  )
}

export default App
