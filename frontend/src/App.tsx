import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet'
import { divIcon } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const routeCoordinates: [number, number][] = [
  [41.8781, -87.6298],
  [38.627, -90.1994],
  [32.7767, -96.797],
]

const stopIcon = divIcon({
  className: 'custom-map-pin',
  html: '<span></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 18],
})

function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="wordmark" aria-label="ELD Trip Planner home">
          <span className="wordmark-mark" aria-hidden="true">
            E
          </span>
          <span>ELD Trip Planner</span>
        </div>
        <span className="topbar-section">TRIP DESK</span>
      </header>

      <main className="workspace" aria-labelledby="page-title">
        <div className="top-layout">
          <aside className="planner-panel" aria-label="Trip planner form">
            <div className="section-label">
              <span className="section-dot" aria-hidden="true" />
              ROUTE PLANNING
            </div>

            <h1 id="page-title">ELD Trip Planner</h1>

            <form className="trip-form" aria-label="Trip planning form">
              <div className="field-group">
                <label htmlFor="current-location">Current location</label>
                <input id="current-location" name="current-location" defaultValue="Chicago, IL" />
              </div>

              <div className="field-group">
                <label htmlFor="pickup-location">Pickup location</label>
                <input id="pickup-location" name="pickup-location" defaultValue="St. Louis, MO" />
              </div>

              <div className="field-group">
                <label htmlFor="dropoff-location">Dropoff location</label>
                <input id="dropoff-location" name="dropoff-location" defaultValue="Dallas, TX" />
              </div>

              <div className="field-row">
                <div className="field-group cycle-field">
                  <label htmlFor="cycle-used">Cycle used</label>
                  <input id="cycle-used" name="cycle-used" type="number" min="0" max="70" defaultValue="12" />
                </div>
                <input className="slider" type="range" min="0" max="70" defaultValue="12" aria-label="Cycle used sliding control" />
              </div>

              <div className="field-group">
                <label htmlFor="start-time">Start date/time</label>
                <input id="start-time" name="start-time" type="datetime-local" defaultValue="2026-10-05T08:00" />
              </div>

              <details className="details-panel" open>
                <summary>Log sheet details</summary>
                <div className="detail-fields">
                  <input placeholder="Driver name" aria-label="Driver name" />
                  <input placeholder="Co-driver" aria-label="Co-driver" />
                  <input placeholder="Carrier name" aria-label="Carrier name" />
                </div>
              </details>

              <button type="submit" className="primary-button">
                Plan trip
              </button>
            </form>
          </aside>

          <section className="map-panel" aria-label="Map of the planned trip">
            <div className="map-frame">
              <MapContainer center={[39.5, -90.7]} zoom={4} scrollWheelZoom={false} className="map-container">
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Polyline positions={routeCoordinates} pathOptions={{ color: '#2f6fef', weight: 4 }} />
                {routeCoordinates.map((point, index) => (
                  <Marker key={`${point[0]}-${point[1]}`} position={point} icon={stopIcon}>
                    <Popup>
                      {index === 0 ? 'Current location' : index === 1 ? 'Pickup' : 'Dropoff'}
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
            <div className="map-legend" aria-label="Stop legend">
              <span><i className="legend-dot start" /> Start</span>
              <span><i className="legend-dot pickup" /> Pickup</span>
              <span><i className="legend-dot dropoff" /> Dropoff</span>
            </div>
          </section>
        </div>

        <section className="lower-grid">
          <div className="summary-card panel-box">
            <h2>Trip summary</h2>
            <div className="stats-grid">
              <div>
                <span className="stat-label">Total miles</span>
                <strong>1,010</strong>
              </div>
              <div>
                <span className="stat-label">Driving hours</span>
                <strong>17.5</strong>
              </div>
              <div>
                <span className="stat-label">Trip time</span>
                <strong>31.8h</strong>
              </div>
              <div>
                <span className="stat-label">Arrival</span>
                <strong>Oct 06, 15:00</strong>
              </div>
            </div>
          </div>

          <div className="schedule-card panel-box">
            <h2>Stop schedule</h2>
            <ul className="stop-list">
              <li><span>08:00</span> Current location</li>
              <li><span>10:30</span> Pickup</li>
              <li><span>12:15</span> Drive to Dallas</li>
              <li><span>15:00</span> Dropoff</li>
            </ul>
          </div>

          <div className="assumptions-card panel-box">
            <h2>Assumptions</h2>
            <ul>
              <li>10+ hours off before trip start.</li>
              <li>Home terminal time is the current location timezone.</li>
              <li>Fuel stop every 1,000 miles at 30 minutes ON.</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
