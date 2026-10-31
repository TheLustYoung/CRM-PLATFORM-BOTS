/** Small dependency-free SVG charts that follow the theme colors (CSS variables). */

export function Sparkline({values, color = 'var(--primary)'}: {values: number[]; color?: string}) {
  const width = 120, height = 40, max = Math.max(1, ...values);
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${(height - 4 - (v / max) * (height - 8)).toFixed(1)}`);
  const id = 'spark' + color.replace(/[^a-z]/gi, '');
  return <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={color} stopOpacity="0.35"/><stop offset="100%" stopColor={color} stopOpacity="0"/>
    </linearGradient></defs>
    {points.length > 1 && <>
      <polygon points={`0,${height} ${points.join(' ')} ${width},${height}`} fill={`url(#${id})`}/>
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke"/>
    </>}
  </svg>;
}

export type Series = {key: string; label: string; color: string};

/** Stacked bars per day; labels under the bars, totals above. */
export function StackedBars({days, series, data, label}: {days: string[]; series: Series[]; data: Record<string, Record<string, number>>;
  label?: (day: string) => string}) {
  const totals = days.map(d => series.reduce((sum, s) => sum + (data[d]?.[s.key] ?? 0), 0));
  const max = Math.max(1, ...totals);
  return <div className="stacked">
    <div className="stacked-bars">{days.map((day, i) => <div key={day} className="stacked-col" title={`${day}: ${totals[i]}`}>
      <span className="stacked-total">{totals[i] || ''}</span>
      <div className="stacked-track">
        <div className="stacked-fill" style={{height: `${(totals[i] / max) * 100}%`}}>
          {series.map(s => {
            const v = data[day]?.[s.key] ?? 0;
            return v ? <div key={s.key} style={{flexGrow: v, background: s.color}}/> : null;
          })}
        </div>
      </div>
      <small>{label ? label(day) : new Date(day + 'T00:00:00').toLocaleDateString(undefined, {weekday: 'short'})}</small>
    </div>)}</div>
    <div className="legend">{series.map(s => <span key={s.key}><i style={{background: s.color}}/>{s.label}</span>)}</div>
  </div>;
}

/** Ring with a percentage in the middle. */
export function Donut({value, label, color = 'var(--success)'}: {value: number | null; label: string; color?: string}) {
  const r = 52, c = 2 * Math.PI * r, pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  return <div className="donut">
    <svg viewBox="0 0 140 140" aria-hidden="true">
      <circle cx="70" cy="70" r={r} fill="none" stroke="var(--track)" strokeWidth="14"/>
      <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
        strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 70 70)"/>
    </svg>
    <div className="donut-center"><strong>{value == null ? '—' : `${Math.round(pct)}%`}</strong><small>{label}</small></div>
  </div>;
}

export function Progress({value, max, color = 'var(--primary)'}: {value: number; max: number; color?: string}) {
  return <div className="progress" role="progressbar" aria-valuenow={value} aria-valuemax={max}>
    <div style={{width: `${max ? Math.min(100, (value / max) * 100) : 0}%`, background: color}}/>
  </div>;
}
