import { useEffect, useState } from 'react'
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import { LocationOn, Route } from '@mui/icons-material'
import { MapContainer, Marker, Polyline, Popup, TileLayer } from 'react-leaflet'
import { divIcon } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const theme = createTheme({
  palette: {
    primary: { main: '#005DAC' },
    secondary: { main: '#D83E7F' },
    background: { default: '#EDEBDC', paper: '#FFFEF8' },
  },
})

type LocationSuggestion = {
  label: string
  latitude?: number
  longitude?: number
  place?: string
}

const defaultLocations: LocationSuggestion[] = [
  { label: 'Chicago, IL' },
  { label: 'St. Louis, MO' },
  { label: 'Dallas, TX' },
  { label: 'Atlanta, GA' },
  { label: 'Denver, CO' },
  { label: 'Seattle, WA' },
  { label: 'New York, NY' },
  { label: 'Los Angeles, CA' },
]

const routeCoordinates: [number, number][] = [
  [41.8781, -87.6298],
  [38.627, -90.1994],
  [32.7767, -96.797],
]

const stopIcons = ['start', 'pickup', 'dropoff'].map((stopType) =>
  divIcon({
    className: `custom-map-pin ${stopType}`,
    html: '<span></span>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  }),
)

async function fetchSuggestions(query: string): Promise<LocationSuggestion[]> {
  const trimmed = query.trim()
  if (!trimmed) {
    return defaultLocations
  }

  try {
    const response = await fetch(
      `/api/geocode/autocomplete?q=${encodeURIComponent(trimmed)}`,
    )

    if (!response.ok) {
      return defaultLocations.filter((item) =>
        item.label.toLowerCase().includes(trimmed.toLowerCase()),
      )
    }

    const data = (await response.json()) as { suggestions?: LocationSuggestion[] }
    const suggestions = data.suggestions ?? []
    return suggestions.length > 0 ? suggestions : defaultLocations
  } catch {
    return defaultLocations.filter((item) =>
      item.label.toLowerCase().includes(trimmed.toLowerCase()),
    )
  }
}

function LocationField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  const [options, setOptions] = useState<LocationSuggestion[]>(defaultLocations)
  const [inputValue, setInputValue] = useState(value)

  useEffect(() => {
    setInputValue(value)
  }, [value])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchSuggestions(inputValue).then(setOptions)
    }, 250)

    return () => window.clearTimeout(timer)
  }, [inputValue])

  return (
    <Autocomplete
      freeSolo
      fullWidth
      autoHighlight
      value={value}
      inputValue={inputValue}
      onInputChange={(_, nextValue) => {
        setInputValue(nextValue)
        if (nextValue) {
          onChange(nextValue)
        }
      }}
      onChange={(_, nextValue) => {
        const nextLabel = typeof nextValue === 'string' ? nextValue : nextValue?.label ?? ''
        onChange(nextLabel)
        setInputValue(nextLabel)
      }}
      options={options}
      getOptionLabel={(option) =>
        typeof option === 'string' ? option : option.label ?? ''
      }
      renderOption={(props, option) => (
        <Box component="li" {...props} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LocationOn fontSize="small" color="action" />
          <Typography variant="body2">{option.label}</Typography>
        </Box>
      )}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder="Search a city or state"
        />
      )}
    />
  )
}

function App() {
  const [currentLocation, setCurrentLocation] = useState('Chicago, IL')
  const [pickupLocation, setPickupLocation] = useState('St. Louis, MO')
  const [dropoffLocation, setDropoffLocation] = useState('Dallas, TX')
  const [cycleUsed, setCycleUsed] = useState(12)
  const [startDate, setStartDate] = useState('2026-10-05')
  const [startTime, setStartTime] = useState('08:00')

  return (
    <ThemeProvider theme={theme}>
    <Box className="app-shell">
      <Box className="topbar" component="header">
        <Box className="wordmark" aria-label="ELD Trip Planner home">
          <Box className="wordmark-mark" aria-hidden="true">
            E
          </Box>
          <Typography component="span" variant="subtitle1" sx={{ fontWeight: 700 }}>
            ELD Trip Planner
          </Typography>
        </Box>
        <Typography component="span" variant="overline" className="topbar-section">
          TRIP DESK
        </Typography>
      </Box>

      <Box className="workspace" component="main" aria-labelledby="page-title">
        <Box className="top-layout">
          <Box component="aside" className="planner-panel" aria-label="Trip planner form">
            <Box className="section-label">
              <Box className="section-dot" aria-hidden="true" />
              ROUTE PLANNING
            </Box>

            <Typography id="page-title" variant="h3" sx={{ mt: 2, mb: 3, fontWeight: 700 }}>
              ELD Trip Planner
            </Typography>

            <Stack spacing={2.25} component="form" aria-label="Trip planning form">
              <LocationField
                label="Current location"
                value={currentLocation}
                onChange={setCurrentLocation}
              />

              <LocationField
                label="Pickup location"
                value={pickupLocation}
                onChange={setPickupLocation}
              />

              <LocationField
                label="Dropoff location"
                value={dropoffLocation}
                onChange={setDropoffLocation}
              />

              <TextField
                fullWidth
                id="cycle-used"
                label="Cycle used (hours)"
                type="number"
                value={cycleUsed}
                onChange={(event) => setCycleUsed(Number(event.target.value))}
                slotProps={{ htmlInput: { min: 0, max: 70 } }}
                helperText="Hours already used in the current 8-day cycle (0–70)."
              />

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  id="start-date"
                  label="Start date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                  fullWidth
                />
                <TextField
                  id="start-time"
                  label="Start time"
                  type="time"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                  fullWidth
                />
              </Stack>

              <Card variant="outlined" sx={{ borderRadius: 2.5 }}>
                <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                    Log sheet details
                  </Typography>
                  <Stack spacing={1.5}>
                    <TextField size="small" label="Driver name" fullWidth />
                    <TextField size="small" label="Co-driver" fullWidth />
                    <TextField size="small" label="Carrier name" fullWidth />
                  </Stack>
                </CardContent>
              </Card>

              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={<Route />}
              >
                Plan trip
              </Button>
            </Stack>
          </Box>

          <Box component="section" className="map-panel" aria-label="Map of the planned trip">
            <Box className="map-frame">
              <MapContainer center={[39.5, -90.7]} zoom={4} scrollWheelZoom={false} className="map-container">
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Polyline positions={routeCoordinates} pathOptions={{ color: '#005DAC', weight: 4 }} />
                {routeCoordinates.map((point, index) => (
                  <Marker key={`${point[0]}-${point[1]}`} position={point} icon={stopIcons[index]}>
                    <Popup>
                      {index === 0 ? 'Current location' : index === 1 ? 'Pickup' : 'Dropoff'}
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </Box>
            <Box className="map-legend" aria-label="Stop legend">
              <Box component="span">
                <Box component="i" className="legend-dot start" /> Start
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot pickup" /> Pickup
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot dropoff" /> Dropoff
              </Box>
            </Box>
          </Box>
        </Box>

        <Box className="lower-grid">
          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Trip summary
            </Typography>
            <Box className="stats-grid">
              <Box>
                <Typography variant="caption" className="stat-label">
                  Total miles
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>1,010</Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Driving hours
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>17.5</Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Trip time
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>31.8h</Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Arrival
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>Oct 06, 15:00</Typography>
              </Box>
            </Box>
          </Card>

          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Stop schedule
            </Typography>
            <Stack spacing={1.2} sx={{ listStyle: 'none' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">08:00</Typography>
                <Typography variant="body2">Current location</Typography>
              </Box>
              <Divider />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">10:30</Typography>
                <Typography variant="body2">Pickup</Typography>
              </Box>
              <Divider />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">12:15</Typography>
                <Typography variant="body2">Drive to Dallas</Typography>
              </Box>
              <Divider />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">15:00</Typography>
                <Typography variant="body2">Dropoff</Typography>
              </Box>
            </Stack>
          </Card>

          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Assumptions
            </Typography>
            <Stack spacing={1}>
              <Chip label="10+ hours off before trip start" color="primary" variant="outlined" />
              <Chip label="Home terminal timezone follows current location" color="primary" variant="outlined" />
              <Chip label="Fuel stop every 1,000 miles" color="primary" variant="outlined" />
            </Stack>
          </Card>
        </Box>
      </Box>
    </Box>
    </ThemeProvider>
  )
}

export default App
