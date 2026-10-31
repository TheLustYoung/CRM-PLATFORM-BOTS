import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {useResource} from '../services/useResource';
import {Messages} from '../components/ui';
import {StackedBars} from '../components/charts';
import {Icon} from '../components/Icon';
import type {Row} from '../services/api';

const PERIODS = {day: 30, week: 12, month: 12} as const;
type Period = keyof typeof PERIODS;
const BOTS = ['', 'video', 'media', 'files'];
const number = (value: number, lang: string) => new Intl.NumberFormat(lang).format(value || 0);
const bytes = (value: number) => value >= 1e9 ? `${(value / 1e9).toFixed(1)} GB` : `${(value / 1e6).toFixed(1)} MB`;
const money = (key: string, amount: number) => key.endsWith(':XTR') ? `${amount} ⭐` : `$${(amount / 100).toFixed(2)}`;

function Breakdown({title, values, format}: {title: string; values: Record<string, number>; format?: (k: string, v: number) => string}) {
  const {lang} = useI18n();
  const entries = Object.entries(values ?? {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(e => e[1]));
  return <section className="panel">
    <div className="panel-title"><h2>{title}</h2></div>
    {!entries.length && <p className="empty">—</p>}
    <ul className="breakdown">{entries.map(([key, value]) => <li key={key}>
      <span>{key}</span><strong>{format ? format(key, value) : number(value, lang)}</strong>
      <div className="progress"><div style={{width: `${(value / max) * 100}%`, background: 'var(--primary)'}}/></div>
    </li>)}</ul>
  </section>;
}

/** daily, weekly and monthly reports by bot, service and platform, with error rates, revenue and storage. */
export function Reports({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const [period, setPeriod] = useState<Period>('day');
  const [bot, setBot] = useState('');
  const query = `period=${period}&count=${PERIODS[period]}${bot ? `&bot=${bot}` : ''}`;
  const report = useResource<Row | null>(`admin/analytics?${query}&r=${revision}`, null);
  const data = report.data;
  const series: Row[] = data?.series ?? [];
  const totals = series.reduce((sum, row) => ({downloads: sum.downloads + row.downloads, uploads: sum.uploads + row.uploads,
    failed: sum.failed + row.failed, completed: sum.completed + row.completed, newUsers: sum.newUsers + row.new_users}),
    {downloads: 0, uploads: 0, failed: 0, completed: 0, newUsers: 0});
  const errorRate = totals.completed + totals.failed ? (100 * totals.failed / (totals.completed + totals.failed)).toFixed(1) : '0';
  const chart = Object.fromEntries(series.map(row => [row.period, {completed: row.completed, failed: row.failed}]));
  return <>
    <Messages error={report.error}/>
    <section className="panel settings">
      <div className="row-actions">
        {(Object.keys(PERIODS) as Period[]).map(p => <button key={p} className={p === period ? 'primary' : ''} onClick={() => setPeriod(p)}>{t('period_' + p)}</button>)}
        <select aria-label={t('bots')} value={bot} onChange={e => setBot(e.target.value)}>
          {BOTS.map(b => <option key={b} value={b}>{b || t('allBots')}</option>)}
        </select>
        <a className="button" href={`/api/admin/analytics.csv?${query}`} download><Icon name="jobs" size={16}/> CSV</a>
      </div>
    </section>
    {data && <>
      <section className="stats">
        {[['rDownloads', totals.downloads], ['rUploads', totals.uploads], ['newUsersPeriod', totals.newUsers]].map(([key, value]) =>
          <article className="stat" key={key as string}><span>{t(key as string)}</span><strong>{number(value as number, lang)}</strong></article>)}
        <article className="stat"><span>{t('errorRate')}</span><strong>{errorRate}%</strong></article>
        <article className="stat"><span>{t('storageUsed')}</span><strong>{bytes(data.storage?.bytes ?? 0)}</strong><small>{number(data.storage?.files ?? 0, lang)} {t('files')}</small></article>
      </section>
      <section className="panel">
        <div className="panel-title"><h2>{t('completedFailed')}</h2></div>
        <StackedBars days={series.map(r => r.period)} data={chart} label={day => period === 'month' ? day : day.slice(5)}
          series={[{key: 'completed', label: t('completed'), color: 'var(--success)'}, {key: 'failed', label: t('failed'), color: 'var(--danger)'}]}/>
      </section>
      <section className="panel">
        <div className="table-wrap"><table>
          <thead><tr>{['period', 'rDownloads', 'rUploads', 'completed', 'failed', 'errorRate', 'activeUsersPeriod', 'newUsersPeriod', 'revenue'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
          <tbody>{[...series].reverse().map(row => <tr key={row.period}>
            <td data-label={t('period')}>{row.period}</td><td data-label={t('rDownloads')}>{row.downloads}</td><td data-label={t('rUploads')}>{row.uploads}</td>
            <td data-label={t('completed')}>{row.completed}</td><td data-label={t('failed')}>{row.failed}</td><td data-label={t('errorRate')}>{row.error_rate}%</td>
            <td data-label={t('activeUsersPeriod')}>{row.active_users}</td><td data-label={t('newUsersPeriod')}>{row.new_users}</td>
            <td data-label={t('revenue')}>{Object.entries(row.revenue ?? {}).map(([k, v]) => `${k.split(':')[0]}: ${money(k, v as number)}`).join(' · ') || '—'}</td>
          </tr>)}</tbody>
        </table></div>
      </section>
      <div className="grid-2">
        <Breakdown title={t('byPlatform')} values={data.by_platform}/>
        <Breakdown title={t('byBot')} values={data.by_bot}/>
        <Breakdown title={t('byService')} values={data.by_service}/>
        <Breakdown title={t('failedByPlatform')} values={data.failed_by_platform}/>
        <Breakdown title={t('topErrors')} values={data.errors}/>
        <Breakdown title={t('revenueByMethod')} values={data.revenue_by_method} format={money}/>
      </div>
      <p className="hint">{t('reportRules')}</p>
    </>}
  </>;
}
