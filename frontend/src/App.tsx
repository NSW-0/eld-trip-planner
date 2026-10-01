import { useEffect, useRef, useState, type FormEvent, type RefObject } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import { ExpandMore, LocationOn, Print, Route } from '@mui/icons-material'
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet'
import { divIcon, type Map as LeafletMap } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'
import LogSheet, { type DailyLogDay } from './components/LogSheet'

const theme = createTheme({
  palette: {
    primary: { main: '#005DAC' },
    secondary: { main: '#D83E7F' },
    background: { default: '#EDEBDC', paper: '#FFFEF8' },
  },
})

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const EMPTY_ROUTE: [number, number][] = []

type LocationSuggestion = {
  label: string
  latitude?: number
  longitude?: number
  place?: string
}

type TripStop = {
  type: string
  lat: number
  lng: number
  place: string
  arrival: string
  departure: string
  duration_hours: number
  note: string
}

type TripPlan = {
  route: {
    geometry: [number, number][]
    total_miles: number
    total_hours: number
    provider: string
    legs: { distance_miles: number; duration_hours: number }[]
  }
  stops: TripStop[]
  summary: {
    total_miles: number
    total_driving_hours: number
    total_on_duty_hours: number
    total_trip_duration_hours: number
    arrival_time: string
    trip_days: number
    cycle_hours_remaining: number
  }
  days: DailyLogDay[]
  assumptions: Record<string, string>
  warnings: string[]
}

type LogDetails = {
  driver_name: string
  co_driver: string
  carrier_name: string
  main_office_address: string
  home_terminal_address: string
  truck_number: string
  trailer_number: string
  shipping_document_number: string
  shipper_commodity: string
}

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`
}

function todayInputValue() {
  const today = new Date()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${today.getFullYear()}-${month}-${day}`
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)
}

function formatLocalTime(value: string) {
  const time = value.split('T')[1]
  return time ? time.slice(0, 5) : value
}

function formatLocalDateTime(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

function stopIcon(stopType: string) {
  return divIcon({
    className: `custom-map-pin ${stopType}`,
    html: '<span></span>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

async function fetchSuggestions(query: string): Promise<LocationSuggestion[]> {
  const trimmed = query.trim()
  if (!trimmed) {
    return []
  }

  try {
    const response = await fetch(apiUrl(`/geocode/autocomplete?q=${encodeURIComponent(trimmed)}`))
    if (!response.ok) {
      return []
    }

    const data = (await response.json()) as { suggestions?: LocationSuggestion[] }
    return data.suggestions ?? []
  } catch {
    return []
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
  const [options, setOptions] = useState<LocationSuggestion[]>([])
  const [inputValue, setInputValue] = useState(value)

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
        onChange(nextValue)
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

function MapViewport({
  coordinates,
  mapRef,
}: {
  coordinates: [number, number][]
  mapRef: RefObject<LeafletMap | null>
}) {
  const map = useMap()

  useEffect(() => {
    mapRef.current = map
    if (coordinates.length > 1) {
      map.fitBounds(coordinates, { padding: [24, 24] })
    } else if (coordinates.length === 1) {
      map.setView(coordinates[0], 7)
    }
  }, [coordinates, map, mapRef])

  return null
}

function App() {
  const [currentLocation, setCurrentLocation] = useState('Chicago, IL')
  const [pickupLocation, setPickupLocation] = useState('St. Louis, MO')
  const [dropoffLocation, setDropoffLocation] = useState('Dallas, TX')
  const [cycleUsed, setCycleUsed] = useState(12)
  const [startDate, setStartDate] = useState(todayInputValue)
  const [startTime, setStartTime] = useState('08:00')
  const [logDetails, setLogDetails] = useState<LogDetails>({
    driver_name: '',
    co_driver: '',
    carrier_name: '',
    main_office_address: '',
    home_terminal_address: '',
    truck_number: '',
    trailer_number: '',
    shipping_document_number: '',
    shipper_commodity: '',
  })
  const [plan, setPlan] = useState<TripPlan | null>(null)
  const [activeLogDay, setActiveLogDay] = useState(0)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const mapRef = useRef<LeafletMap | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    if (!currentLocation.trim() || !pickupLocation.trim() || !dropoffLocation.trim()) {
      setError('Enter a current location, pickup, and dropoff.')
      return
    }
    if (!Number.isFinite(cycleUsed) || cycleUsed < 0 || cycleUsed > 70) {
      setError('Cycle used must be between 0 and 70 hours.')
      return
    }
    if (!startDate || !startTime) {
      setError('Enter both a start date and start time.')
      return
    }

    setIsSubmitting(true)
    setPlan(null)
    try {
      const response = await fetch(apiUrl('/trips/plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_location: currentLocation.trim(),
          pickup_location: pickupLocation.trim(),
          dropoff_location: dropoffLocation.trim(),
          current_cycle_used_hours: cycleUsed,
          start_datetime: `${startDate}T${startTime}:00`,
          log_details: logDetails,
        }),
      })
      const data = (await response.json()) as TripPlan | { error?: string }
      if (!response.ok) {
        throw new Error('error' in data ? data.error : 'Unable to plan this trip.')
      }
      setPlan(data as TripPlan)
      setActiveLogDay(0)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to plan this trip. Check your connection and try again.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const routeCoordinates = plan?.route.geometry ?? EMPTY_ROUTE

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

            <Stack
              spacing={2.25}
              component="form"
              aria-label="Trip planning form"
              onSubmit={handleSubmit}
            >
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
                onChange={(event) =>
                  setCycleUsed(event.target.value === '' ? Number.NaN : Number(event.target.value))
                }
                slotProps={{ htmlInput: { min: 0, max: 70 } }}
                helperText="Hours already used in the current 8-day cycle (0–70)."
                required
              />

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  id="start-date"
                  label="Start date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                  required
                  fullWidth
                />
                <TextField
                  id="start-time"
                  label="Start time"
                  type="time"
                  value={startTime}
                  onChange={(event) => setStartTime(event.target.value)}
                  slotProps={{ inputLabel: { shrink: true } }}
                  required
                  fullWidth
                />
              </Stack>

              <Accordion className="log-details-accordion" disableGutters>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    Log sheet details
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={1.5}>
                    <TextField
                      size="small"
                      label="Driver name"
                      value={logDetails.driver_name}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, driver_name: event.target.value })
                      }
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="Co-driver"
                      value={logDetails.co_driver}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, co_driver: event.target.value })
                      }
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="Carrier name"
                      value={logDetails.carrier_name}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, carrier_name: event.target.value })
                      }
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="Main office address"
                      value={logDetails.main_office_address}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, main_office_address: event.target.value })
                      }
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="Home terminal address"
                      value={logDetails.home_terminal_address}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, home_terminal_address: event.target.value })
                      }
                      fullWidth
                    />
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                      <TextField
                        size="small"
                        label="Truck number"
                        value={logDetails.truck_number}
                        onChange={(event) =>
                          setLogDetails({ ...logDetails, truck_number: event.target.value })
                        }
                        fullWidth
                      />
                      <TextField
                        size="small"
                        label="Trailer number"
                        value={logDetails.trailer_number}
                        onChange={(event) =>
                          setLogDetails({ ...logDetails, trailer_number: event.target.value })
                        }
                        fullWidth
                      />
                    </Stack>
                    <TextField
                      size="small"
                      label="Shipping document number"
                      value={logDetails.shipping_document_number}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, shipping_document_number: event.target.value })
                      }
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="Shipper and commodity"
                      value={logDetails.shipper_commodity}
                      onChange={(event) =>
                        setLogDetails({ ...logDetails, shipper_commodity: event.target.value })
                      }
                      fullWidth
                    />
                  </Stack>
                </AccordionDetails>
              </Accordion>

              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={isSubmitting}
                startIcon={
                  isSubmitting ? <CircularProgress size={18} color="inherit" /> : <Route />
                }
              >
                {isSubmitting ? 'Planning trip' : 'Plan trip'}
              </Button>
              {error && <Alert severity="error">{error}</Alert>}
            </Stack>
          </Box>

          <Box component="section" className="map-panel" aria-label="Map of the planned trip">
            <Box className="map-frame">
              <MapContainer
                center={routeCoordinates[0] ?? [39.5, -90.7]}
                zoom={4}
                scrollWheelZoom={false}
                className="map-container"
              >
                <MapViewport coordinates={routeCoordinates} mapRef={mapRef} />
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {plan && routeCoordinates.length > 1 && (
                  <Polyline
                    positions={routeCoordinates}
                    pathOptions={{ color: '#005DAC', weight: 4 }}
                  />
                )}
                {plan?.stops.map((stop, index) => (
                  <Marker
                    key={`${stop.type}-${stop.lat}-${stop.lng}-${index}`}
                    position={[stop.lat, stop.lng]}
                    icon={stopIcon(stop.type)}
                  >
                    <Popup>
                      <strong>{stop.place}</strong>
                      <br />
                      {stop.note}
                      <br />
                      {formatLocalTime(stop.arrival)} - {formatLocalTime(stop.departure)}
                      {stop.duration_hours > 0 && ` (${formatNumber(stop.duration_hours)} h)`}
                    </Popup>
                  </Marker>
                ))}
                {!plan && (
                  <Box className="map-empty-label" component="span">
                    Plan a trip to see its route
                  </Box>
                )}
              </MapContainer>
            </Box>
            <Box className="map-legend" aria-label="Stop legend">
              <Box component="span">
                <Box component="i" className="legend-dot start" /> Current
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot pickup" /> Pickup
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot dropoff" /> Dropoff
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot fuel" /> Fuel
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot break" /> Break
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot rest" /> Rest
              </Box>
              <Box component="span">
                <Box component="i" className="legend-dot restart" /> Restart
              </Box>
            </Box>
          </Box>
        </Box>

        <Box className="lower-grid">
          {plan?.warnings.map((warning) => (
            <Alert key={warning} severity="warning" sx={{ gridColumn: '1 / -1' }}>
              {warning}
            </Alert>
          ))}

          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Trip summary
            </Typography>
            <Box className="stats-grid">
              <Box>
                <Typography variant="caption" className="stat-label">
                  Total miles
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? formatNumber(plan.summary.total_miles) : '--'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Driving hours
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? formatNumber(plan.summary.total_driving_hours) : '--'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Trip time
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? `${formatNumber(plan.summary.total_trip_duration_hours)}h` : '--'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Arrival
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? formatLocalDateTime(plan.summary.arrival_time) : '--'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Log days
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? plan.summary.trip_days : '--'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" className="stat-label">
                  Cycle hours left
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {plan ? formatNumber(plan.summary.cycle_hours_remaining) : '--'}
                </Typography>
              </Box>
            </Box>
          </Card>

          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Stop schedule
            </Typography>
            {plan ? (
              <Stack spacing={1.2}>
                {plan.stops.map((stop, index) => (
                  <Box key={`${stop.type}-${stop.arrival}-${index}`}>
                    <Button
                      fullWidth
                      onClick={() =>
                        mapRef.current?.flyTo([stop.lat, stop.lng], Math.max(mapRef.current.getZoom(), 6))
                      }
                      sx={{
                        color: 'text.primary',
                        display: 'flex',
                        justifyContent: 'space-between',
                        textAlign: 'left',
                        textTransform: 'none',
                      }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {formatLocalTime(stop.arrival)}
                      </Typography>
                      <Typography variant="body2">
                        {stop.place} · {stop.note}
                      </Typography>
                    </Button>
                    {index < plan.stops.length - 1 && <Divider />}
                  </Box>
                ))}
              </Stack>
            ) : (
              <Typography color="text.secondary" variant="body2">
                Stop times will appear after planning a trip.
              </Typography>
            )}
          </Card>

          <Card className="panel-box" sx={{ borderRadius: 3, p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Assumptions
            </Typography>
            <Stack spacing={1}>
              {plan ? (
                Object.entries(plan.assumptions).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key === 'home_terminal_timezone' ? 'Time zone' : key}: ${value}`}
                    color="primary"
                    variant="outlined"
                  />
                ))
              ) : (
                <Typography color="text.secondary" variant="body2">
                  Trip assumptions will be shown with the plan.
                </Typography>
              )}
            </Stack>
          </Card>
        </Box>

        {plan && plan.days.length > 0 && (
          <Box component="section" className="log-section" aria-label="Daily log sheets">
            <Box className="log-section-header">
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Daily log sheets
              </Typography>
              <Button startIcon={<Print />} onClick={() => window.print()}>
                Print log
              </Button>
            </Box>
            <Tabs
              value={Math.min(activeLogDay, plan.days.length - 1)}
              onChange={(_, value: number) => setActiveLogDay(value)}
              aria-label="Log sheet day navigation"
              variant="scrollable"
              scrollButtons="auto"
            >
              {plan.days.map((day, index) => (
                <Tab
                  key={day.date}
                  label={`Day ${index + 1} · ${day.date}`}
                  id={`log-tab-${index}`}
                  aria-controls={`log-panel-${index}`}
                />
              ))}
            </Tabs>
            <Box
              id={`log-panel-${activeLogDay}`}
              role="tabpanel"
              aria-labelledby={`log-tab-${activeLogDay}`}
              className="log-sheet-viewport"
            >
              <LogSheet day={plan.days[activeLogDay]} />
            </Box>
          </Box>
        )}
      </Box>
    </Box>
    </ThemeProvider>
  )
}

export default App
