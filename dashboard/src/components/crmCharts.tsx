/** CRM-style charts for the overview. Dependency-free SVG; every value comes from the API (no placeholder data), and
 * each chart carries a visually hidden table so screen readers get the same numbers. */
import {useId} from 'react';

export type Point = {label: string; values: number[]};

const niceMax = (value: number) => {
  if (value <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(value));
  return Math.ceil(value / pow) * pow;
};

function DataTable({caption, columns, rows}: {caption: string; columns: string[]; rows: (string | number)[][]}) {
  return <table className="sr-only"><caption>{caption}</caption>
    <thead><tr>{columns.map(c => <th key={c} scope="col">{c}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{r.map((v, j) => j === 0 ? <th key={j} scope="row">{v}</th> : <td key={j}>{v}</td>)}</tr>)}</tbody>
  </table>;
}

/** Smooth area/line chart for up to three series (e.g. downloads, uploads, links). */
export function AreaChart({points, series, caption}: {points: Point[]; series: {label: string; color: string}[]; caption: string}) {
  const id = useId().replace(/:/g, '');
  const w = 640, h = 220, pad = {l: 34, r: 8, t: 12, b: 26};
  const max = niceMax(Math.max(0, ...points.flatMap(p => p.values)));
  const x = (i: number) => pad.l + (points.length > 1 ? i * (w - pad.l - pad.r) / (points.length - 1) : 0);
  const y = (v: number) => pad.t + (h - pad.t - pad.b) * (1 - v / max);
  const path = (k: number) => points.map((p, i) => {
    const [px, py] = [x(i), y(p.values[k] ?? 0)];
    if (i === 0) return `M${px},${py}`;
    const [qx, qy] = [x(i - 1), y(points[i - 1].values[k] ?? 0)];
    const mid = (qx + px) / 2;
    return `C${mid},${qy} ${mid},${py} ${px},${py}`;  // monotone-looking cubic between points
  }).join(' ');
  const ticks = [0, .25, .5, .75, 1].map(f => Math.round(max * f));
  const every = Math.ceil(points.length / 8);
  return <figure className="area-chart">
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={caption} preserveAspectRatio="none">
      <defs>{series.map((s, k) => <linearGradient key={k} id={`${id}-g${k}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={s.color} stopOpacity={k === 0 ? .42 : .18}/><stop offset="1" stopColor={s.color} stopOpacity="0"/>
      </linearGradient>)}</defs>
      {ticks.map(t => <g key={t}><line className="grid-line" x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)}/>
        <text className="axis" x={pad.l - 8} y={y(t) + 4} textAnchor="end">{t}</text></g>)}
      {points.map((p, i) => i % every === 0 && <text key={p.label} className="axis" x={x(i)} y={h - 6} textAnchor="middle">{p.label}</text>)}
      {series.map((s, k) => points.length > 1 && <g key={s.label}>
        <path d={`${path(k)} L${x(points.length - 1)},${y(0)} L${x(0)},${y(0)} Z`} fill={`url(#${id}-g${k})`}/>
        <path d={path(k)} fill="none" stroke={s.color} strokeWidth={k === 0 ? 2.5 : 1.75} vectorEffect="non-scaling-stroke"/>
        {points.map((p, i) => <circle key={i} cx={x(i)} cy={y(p.values[k] ?? 0)} r={k === 0 ? 3 : 2.25} fill="var(--surface)" stroke={s.color} strokeWidth="1.5" vectorEffect="non-scaling-stroke"/>)}
      </g>)}
    </svg>
    <figcaption className="legend">{series.map(s => <span key={s.label}><i style={{background: s.color}}/>{s.label}</span>)}</figcaption>
    <DataTable caption={caption} columns={['', ...series.map(s => s.label)]} rows={points.map(p => [p.label, ...p.values])}/>
  </figure>;
}

/** Pill-shaped stacked columns: delivered (light) on the bottom, failed (violet) on top — like the reference's bars. */
export function OutcomeBars({days, caption, okLabel, failLabel}: {days: {label: string; ok: number; failed: number}[]; caption: string; okLabel: string; failLabel: string}) {
  const max = niceMax(Math.max(0, ...days.map(d => d.ok + d.failed)));
  return <figure className="outcome-bars">
    <div className="bars" role="img" aria-label={caption}>{days.map(d => <div className="bar-col" key={d.label} title={`${d.label}: ${d.ok} / ${d.failed}`}>
      <div className="bar-track">
        <div className="bar-fail" style={{height: `${(d.failed / max) * 100}%`}}/>
        <div className="bar-ok" style={{height: `${(d.ok / max) * 100}%`}}/>
      </div>
      <small>{d.label}</small>
    </div>)}</div>
    <figcaption className="legend"><span><i className="ok"/>{okLabel}</span><span><i className="fail"/>{failLabel}</span></figcaption>
    <DataTable caption={caption} columns={['', okLabel, failLabel]} rows={days.map(d => [d.label, d.ok, d.failed])}/>
  </figure>;
}

/** Donut with one segment per category and a legend with absolute values. */
export function SegmentDonut({items, caption, total, totalLabel}: {items: {label: string; value: number; color: string}[]; caption: string; total: string; totalLabel: string}) {
  const r = 58, c = 2 * Math.PI * r, sum = items.reduce((a, b) => a + b.value, 0);
  let offset = 0;
  return <figure className="segment-donut">
    <div className="donut-wrap">
      <svg viewBox="0 0 160 160" role="img" aria-label={caption}>
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--track)" strokeWidth="18"/>
        {sum > 0 && items.map(item => {
          const len = (item.value / sum) * c, gap = items.length > 1 ? 3 : 0;
          const el = <circle key={item.label} cx="80" cy="80" r={r} fill="none" stroke={item.color} strokeWidth="18" strokeLinecap="butt"
            strokeDasharray={`${Math.max(0, len - gap)} ${c}`} strokeDashoffset={-offset} transform="rotate(-90 80 80)"/>;
          offset += len;
          return el;
        })}
      </svg>
      <div className="donut-center"><strong>{total}</strong><small>{totalLabel}</small></div>
    </div>
    <ul className="donut-legend">{items.map(item => <li key={item.label}>
      <i style={{background: item.color}}/><span>{item.label}</span><strong>{item.value}</strong>
      <small>{sum ? Math.round((item.value / sum) * 100) : 0}%</small>
    </li>)}</ul>
    <DataTable caption={caption} columns={['', '#']} rows={items.map(i => [i.label, i.value])}/>
  </figure>;
}

/** Horizontal funnel: each step as a frosted bar with its share of the first step. */
export function Funnel({steps, caption}: {steps: {label: string; value: number}[]; caption: string}) {
  const first = Math.max(1, steps[0]?.value ?? 0);
  return <figure className="funnel" aria-label={caption}>
    <ol>{steps.map(s => {
      const pct = Math.round((s.value / first) * 100);
      return <li key={s.label}>
        <div className="funnel-head"><span>{s.label}</span><strong>{s.value}</strong></div>
        <div className="funnel-track"><div style={{width: `${Math.max(pct, s.value ? 4 : 0)}%`}}/><small>{pct}%</small></div>
      </li>;
    })}</ol>
  </figure>;
}

/** Weekday × time-of-day heatmap (3-hour buckets), white → violet by intensity, like "Best send times". */
export function Heatmap({grid, days, caption}: {grid: number[][]; days: string[]; caption: string}) {
  const buckets = Array.from({length: 8}, (_, b) => b * 3);
  const values = grid.map(row => buckets.map(start => row.slice(start, start + 3).reduce((a, b) => a + b, 0)));
  const max = Math.max(1, ...values.flat());
  const level = (v: number) => v === 0 ? 0 : Math.min(4, Math.ceil((v / max) * 4));
  const hour = (h: number) => `${String(h).padStart(2, '0')}`;
  return <figure className="heatmap">
    <div className="heat-grid" role="img" aria-label={caption}>
      <span/>{buckets.map(b => <small key={b} className="heat-col">{hour(b)}–{hour(b + 3)}</small>)}
      {values.map((row, d) => <div className="heat-row" key={d} style={{display: 'contents'}}>
        <small className="heat-day">{days[d]}</small>
        {row.map((v, b) => <span key={b} className={`heat-cell l${level(v)}`} title={`${days[d]} ${hour(buckets[b])}:00–${hour(buckets[b] + 3)}:00 · ${v}`}>{v || ''}</span>)}
      </div>)}
    </div>
    <DataTable caption={caption} columns={['', ...buckets.map(b => `${hour(b)}:00`)]} rows={values.map((row, d) => [days[d], ...row])}/>
  </figure>;
}
