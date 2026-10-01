import type { ReactNode } from 'react'

export type DutyGridSegment = {
  status: 'OFF' | 'SB' | 'D' | 'ON'
  start_minute: number
  end_minute: number
  miles: number
  place: string
  note: string
}

export type DailyLogDay = {
  date: string
  from_place: string
  to_place: string
  total_miles_driving_today: number
  total_hours: number
  on_duty_hours_today: number
  row_totals: Record<'OFF' | 'SB' | 'D' | 'ON', number>
  remarks: string[]
  recap: { A: number; B: number; C: number }
  log_details: {
    driver_name: string
    co_driver: string
    carrier_name: string
    main_office_address: string
    home_terminal_address: string
    truck_number: string
    trailer_number: string
    shipping_document_number: string
    shipper_commodity?: string
  }
  segments: DutyGridSegment[]
}

const GRID_X = 136
const GRID_Y = 300
const GRID_WIDTH = 780
const ROW_HEIGHT = 38
const GRID_HEIGHT = ROW_HEIGHT * 4
const ROW_INDEX: Record<DutyGridSegment['status'], number> = {
  OFF: 0,
  SB: 1,
  D: 2,
  ON: 3,
}

function fieldLine(label: string, value: string, x: number, y: number, width: number) {
  return (
    <g key={`${label}-${x}-${y}`}>
      <line x1={x} y1={y} x2={x + width} y2={y} stroke="#3d4549" strokeWidth="1" />
      <text x={x} y={y + 12} className="log-sheet-label">
        {label}
      </text>
      <text x={x + 4} y={y - 6} className="log-sheet-value">
        {value}
      </text>
    </g>
  )
}

function dutyPath(segments: DutyGridSegment[]) {
  if (segments.length === 0) return ''
  const xAt = (minute: number) => GRID_X + (minute / 1440) * GRID_WIDTH
  const yAt = (status: DutyGridSegment['status']) =>
    GRID_Y + ROW_INDEX[status] * ROW_HEIGHT + ROW_HEIGHT / 2
  let path = `M ${xAt(segments[0].start_minute)} ${yAt(segments[0].status)}`
  segments.forEach((segment, index) => {
    path += ` H ${xAt(segment.end_minute)}`
    const next = segments[index + 1]
    if (next && next.status !== segment.status) {
      path += ` V ${yAt(next.status)}`
    }
  })
  return path
}

function SvgText({ children, ...props }: { children: ReactNode } & React.SVGProps<SVGTextElement>) {
  return <text {...props}>{children}</text>
}

export default function LogSheet({ day }: { day: DailyLogDay }) {
  const dateParts = day.date.split('-')
  const dateLabel = `${dateParts[1]}/${dateParts[2]}/${dateParts[0]}`
  const remarksColumns = 3
  const remarkRows = Math.max(4, Math.ceil(day.remarks.length / remarksColumns))
  const remarksY = GRID_Y + GRID_HEIGHT + 68
  const shippingY = remarksY + remarkRows * 18 + 38
  const recapY = shippingY + 105
  const svgHeight = recapY + 150
  const xAt = (minute: number) => GRID_X + (minute / 1440) * GRID_WIDTH
  const statusLabels: { status: DutyGridSegment['status']; label: string }[] = [
    { status: 'OFF', label: '1. Off Duty' },
    { status: 'SB', label: '2. Sleeper Berth' },
    { status: 'D', label: '3. Driving' },
    { status: 'ON', label: '4. On Duty (not driving)' },
  ]

  return (
    <svg
      className="log-sheet-svg"
      viewBox={`0 0 1080 ${svgHeight}`}
      role="img"
      aria-label={`Driver's Daily Log for ${day.date}`}
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>Driver's Daily Log for {day.date}</title>
      <rect x="0" y="0" width="1080" height={svgHeight} fill="#FFFEF8" />

      <SvgText x="28" y="38" className="log-sheet-title">
        Driver's Daily Log
      </SvgText>
      <SvgText x="28" y="57" className="log-sheet-small">
        (24 hours)
      </SvgText>
      <SvgText x="675" y="24" className="log-sheet-small">
        Original - File at home terminal.
      </SvgText>
      <SvgText x="675" y="42" className="log-sheet-small">
        Duplicate - Driver retains in his/her possession for 8 days.
      </SvgText>
      {fieldLine('Date (month / day / year)', dateLabel, 660, 78, 280)}
      {fieldLine('From', day.from_place, 28, 112, 435)}
      {fieldLine('To', day.to_place, 510, 112, 430)}

      <rect x="28" y="135" width="192" height="44" fill="none" stroke="#3d4549" />
      <SvgText x="35" y="153" className="log-sheet-value">
        {day.total_miles_driving_today.toFixed(0)}
      </SvgText>
      <SvgText x="35" y="172" className="log-sheet-label">
        Total Miles Driving Today
      </SvgText>
      <rect x="230" y="135" width="192" height="44" fill="none" stroke="#3d4549" />
      <SvgText x="237" y="153" className="log-sheet-value">
        {day.total_miles_driving_today.toFixed(0)}
      </SvgText>
      <SvgText x="237" y="172" className="log-sheet-label">
        Total Mileage Today
      </SvgText>
      {fieldLine('Name of Carrier or Carriers', day.log_details.carrier_name, 455, 158, 485)}
      {fieldLine('Main Office Address', day.log_details.main_office_address, 455, 193, 485)}
      {fieldLine('Home Terminal Address', day.log_details.home_terminal_address, 455, 228, 485)}
      {fieldLine(
        'Truck / Tractor and Trailer Numbers',
        `${day.log_details.truck_number} / ${day.log_details.trailer_number}`,
        28,
        220,
        394,
      )}
      {fieldLine('Driver', day.log_details.driver_name, 28, 258, 210)}
      {fieldLine('Co-driver', day.log_details.co_driver || 'None', 250, 258, 172)}

      <rect x="28" y={GRID_Y - 28} width={GRID_X - 28} height="28" fill="#172227" />
      <rect x={GRID_X} y={GRID_Y - 28} width={GRID_WIDTH} height="28" fill="#172227" />
      <SvgText x="34" y={GRID_Y - 9} className="log-sheet-grid-heading">
        Midnight
      </SvgText>
      {Array.from({ length: 24 }, (_, hour) => {
        const x = xAt((hour + 0.5) * 60) - 4
        const label = hour === 12 ? 'Noon' : String(hour > 12 ? hour - 12 : hour === 0 ? 12 : hour)
        return (
          <SvgText
            key={hour}
            x={x + 2}
            y={GRID_Y - 9}
            className="log-sheet-grid-heading"
          >
            {label}
          </SvgText>
        )
      })}
      <SvgText x={GRID_X + GRID_WIDTH + 14} y={GRID_Y - 9} className="log-sheet-grid-heading">
        Total
      </SvgText>

      <rect x={GRID_X} y={GRID_Y} width={GRID_WIDTH} height={GRID_HEIGHT} fill="none" stroke="#273238" />
      {Array.from({ length: 97 }, (_, tick) => {
        const minute = tick * 15
        const x = xAt(minute)
        const isHour = tick % 4 === 0
        return (
          <line
            key={tick}
            x1={x}
            y1={GRID_Y}
            x2={x}
            y2={GRID_Y + GRID_HEIGHT}
            stroke={isHour ? '#737c80' : '#c5c9c8'}
            strokeWidth={isHour ? 0.9 : 0.45}
          />
        )
      })}
      {Array.from({ length: 5 }, (_, row) => (
        <line
          key={row}
          x1={GRID_X}
          y1={GRID_Y + row * ROW_HEIGHT}
          x2={GRID_X + GRID_WIDTH}
          y2={GRID_Y + row * ROW_HEIGHT}
          stroke="#737c80"
          strokeWidth="0.8"
        />
      ))}
      {statusLabels.map(({ status, label }) => (
        <g key={status}>
          <SvgText x="28" y={GRID_Y + ROW_INDEX[status] * ROW_HEIGHT + 17} className="log-sheet-row-label">
            {label}
          </SvgText>
          <SvgText
            x={GRID_X + GRID_WIDTH + 18}
            y={GRID_Y + ROW_INDEX[status] * ROW_HEIGHT + 17}
            className="log-sheet-value"
          >
            {day.row_totals[status].toFixed(2)}
          </SvgText>
        </g>
      ))}
      <SvgText x={GRID_X + GRID_WIDTH + 15} y={GRID_Y - 35} className="log-sheet-label">
        Total Hours
      </SvgText>
      <path
        data-testid="duty-line"
        d={dutyPath(day.segments)}
        fill="none"
        stroke="#005DAC"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {day.segments.slice(1).map((segment, index) => (
        <line
          key={`change-${index}`}
          x1={xAt(segment.start_minute)}
          y1={GRID_Y + GRID_HEIGHT + 1}
          x2={xAt(segment.start_minute)}
          y2={GRID_Y + GRID_HEIGHT + 9}
          stroke="#172227"
          strokeWidth="1"
        />
      ))}

      <SvgText x="28" y={remarksY} className="log-sheet-section-title">
        Remarks
      </SvgText>
      <line x1="28" y1={remarksY + 8} x2="940" y2={remarksY + 8} stroke="#3d4549" />
      {day.remarks.map((remark, index) => {
        const column = Math.floor(index / remarkRows)
        const row = index % remarkRows
        return (
          <SvgText
            key={`${remark}-${index}`}
            x={28 + column * 305}
            y={remarksY + 28 + row * 18}
            className="log-sheet-remark"
          >
            {remark}
          </SvgText>
        )
      })}

      <line x1="28" y1={shippingY} x2="940" y2={shippingY} stroke="#3d4549" />
      <SvgText x="28" y={shippingY + 22} className="log-sheet-section-title">
        Shipping Documents
      </SvgText>
      {fieldLine('DVL or Manifest No.', day.log_details.shipping_document_number, 28, shippingY + 66, 340)}
      {fieldLine('Shipper & Commodity', day.log_details.shipper_commodity || '', 390, shippingY + 66, 550)}
      <SvgText x="28" y={shippingY + 91} className="log-sheet-small">
        Enter name of place you reported and where released from work and when and where each change of duty occurred.
      </SvgText>

      <line x1="28" y1={recapY} x2="940" y2={recapY} stroke="#3d4549" />
      <SvgText x="28" y={recapY + 22} className="log-sheet-section-title">
        Recap: Complete at end of day
      </SvgText>
      <SvgText x="28" y={recapY + 47} className="log-sheet-label">
        On duty hours today (lines 3 &amp; 4)
      </SvgText>
      <SvgText x="28" y={recapY + 73} className="log-sheet-value">
        {day.on_duty_hours_today.toFixed(2)}
      </SvgText>
      <SvgText x="320" y={recapY + 22} className="log-sheet-section-title">
        70 Hour / 8 Day
      </SvgText>
      {(['A', 'B', 'C'] as const).map((letter, index) => (
        <g key={letter}>
          <SvgText x={320 + index * 175} y={recapY + 47} className="log-sheet-label">
            {letter}. {index === 0 ? 'Last 7 days' : index === 1 ? 'Available tomorrow' : 'Last 5 days'}
          </SvgText>
          <SvgText x={320 + index * 175} y={recapY + 73} className="log-sheet-value">
            {day.recap[letter].toFixed(2)}
          </SvgText>
        </g>
      ))}
      <SvgText x="845" y={recapY + 22} className="log-sheet-section-title">
        60 Hour / 7 Day
      </SvgText>
      <SvgText x="845" y={recapY + 55} className="log-sheet-value">
        N/A
      </SvgText>
      <SvgText x="28" y={recapY + 112} className="log-sheet-small">
        A 34-hour consecutive off-duty / sleeper-berth break makes the full 70 hours available.
      </SvgText>
    </svg>
  )
}