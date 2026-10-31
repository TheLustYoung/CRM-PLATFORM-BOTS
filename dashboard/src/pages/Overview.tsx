import {useI18n} from '../services/i18n';
import {useResource} from '../services/useResource';
import {bytes, dateTime, number} from '../services/format';
import {Messages} from '../components/ui';
import {Icon} from '../components/Icon';
import {BotGuideCards} from '../components/BotGuide';
import {Progress, Sparkline} from '../components/charts';
import {AreaChart, Funnel, Heatmap, OutcomeBars, SegmentDonut} from '../components/crmCharts';
import {BOT_ICONS, sourceTitle} from '../services/sources';
import type {Page} from '../components/Sidebar';
import type {Row} from '../services/api';

const KPIS: {key: string; label: string; icon: string; spark?: string}[] = [
  {key: 'users', label: 'users_count', icon: 'users'},
  {key: 'active_users', label: 'active_users', icon: 'activity'},
  {key: 'downloads', label: 'downloads', icon: 'jobs', spark: 'download'},
  {key: 'uploads', label: 'uploads', icon: 'upload', spark: 'upload'},
  {key: 'new_users_week', label: 'new_users_week', icon: 'userPlus'},
  {key: 'active_jobs', label: 'active_jobs', icon: 'clock'},
  {key: 'files', label: 'files_count', icon: 'folder'},
  {key: 'storage_bytes', label: 'storage_bytes', icon: 'storage'},
];
const SOURCE_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-5)', 'var(--chart-4)'];

const isoDay = (offset: number) => new Date(Date.now() - offset * 864e5).toISOString().slice(0, 10);
const lastDays = (n: number) => Array.from({length: n}, (_, i) => isoDay(n - 1 - i));

export function Overview({revision, user, onNavigate}: {revision: number; user: string; onNavigate: (p: Page) => void}) {
  const {t, lang} = useI18n();
  const stats = useResource<Row>(`admin/overview?r=${revision}`, {});
  const compat = useResource<Row[]>(`admin/compatibility?r=${revision}`, []);
  const s = stats.data;
  const short = (day: string, opts: Intl.DateTimeFormatOptions) => new Date(day + 'T00:00:00Z').toLocaleDateString(lang, {...opts, timeZone: 'UTC'});

  const week = lastDays(7);
  const byDay: Record<string, Record<string, number>> = {};
  (s.daily ?? []).forEach((d: Row) => { (byDay[d.date] ??= {})[d.kind] = d.count; });
  const seriesFor = (kind: string) => week.map(d => byDay[d]?.[kind] ?? 0);
  const todayJobs = Object.values(byDay[week[6]] ?? {}).reduce((a, b) => a + b, 0);

  const month = lastDays(14);
  const outcome = month.map(day => ({label: short(day, {day: 'numeric'}), ok: s.outcome?.[day]?.completed ?? 0, failed: s.outcome?.[day]?.failed ?? 0}));
  const sources = Object.entries((s.sources ?? {}) as Record<string, number>).sort((a, b) => b[1] - a[1])
    .map(([key, value], i) => ({label: sourceTitle(key), value, color: SOURCE_COLORS[i % SOURCE_COLORS.length]}));
  const sourceTotal = sources.reduce((a, b) => a + b.value, 0);
  const funnel = s.funnel ?? {links: 0, downloads: 0, delivered: 0};
  const weekdays = Array.from({length: 7}, (_, i) => new Date(Date.UTC(2026, 9, 26 + i)).toLocaleDateString(lang, {weekday: 'short', timeZone: 'UTC'}));

  const ok = s.successful_downloads ?? 0, bad = s.failed_downloads ?? 0;
  const rate = ok + bad ? Math.round((ok / (ok + bad)) * 100) : null;
  const perBot: Record<string, Record<string, number>> = {};
  (s.bots ?? []).forEach((b: Row) => { (perBot[b.bot_id] ??= {})[b.status] = b.count; });
  const botTotals = Object.entries(perBot).map(([bot, c]) => ({bot, c, total: Object.values(c).reduce((a, b) => a + b, 0)}));
  const maxBot = Math.max(1, ...botTotals.map(b => b.total));
  const value = (key: string) => s[key] === undefined ? '—' : key === 'storage_bytes' ? bytes(s[key]) : number(s[key], lang);
  const days = s.activity_days ?? 30;

  return <div className="crm">
    <Messages error={stats.error || compat.error}/>

    <div className="crm-intro">
      <div>
        <h2>{t('welcomeBack').replace('{name}', user)}</h2>
        <p>{t('welcomeSub')}</p>
      </div>
      <div className="chips">
        {s.demo_data ? <span className="chip demo" title={t('crmDemoHint')}><i/>{t('crmDemo')}</span> : <span className="chip live"><i/>{t('crmLive')}</span>}
        <span className="chip">{t('crmToday').replace('{count}', number(todayJobs, lang))}</span>
        <span className="chip">{t('successRate')}: {rate == null ? '—' : `${rate}%`}</span>
        <button className="chip action" onClick={() => onNavigate('jobs')}>{t('viewDownloads')} <Icon name="arrowRight" size={14}/></button>
      </div>
    </div>

    <div className="kpi-strip">{KPIS.map(k => <article key={k.key} className="kpi">
      <div className="kpi-head"><span>{t(k.label)}</span><Icon name={k.icon} size={15}/></div>
      <strong>{value(k.key)}</strong>
      {k.spark && <Sparkline values={seriesFor(k.spark)} color="var(--chart-1)"/>}
    </article>)}</div>

    <div className="crm-grid">
      <section className="card span-8">
        <div className="card-head"><h2><Icon name="activity" size={16}/>{t('crmActivity')}</h2><span className="chip">7d</span></div>
        <AreaChart caption={t('crmActivity')} points={week.map(d => ({label: short(d, {weekday: 'short'}), values: [byDay[d]?.download ?? 0, byDay[d]?.metadata ?? 0, byDay[d]?.upload ?? 0]}))}
          series={[{label: t('download'), color: 'var(--chart-1)'}, {label: t('metadata'), color: 'var(--chart-2)'}, {label: t('upload'), color: 'var(--chart-5)'}]}/>
      </section>

      <section className="card span-4 glass">
        <div className="card-head"><h2><Icon name="image" size={16}/>{t('crmSources')}</h2><span className="chip">{days}d</span></div>
        {sources.length ? <SegmentDonut caption={t('crmSources')} items={sources} total={number(sourceTotal, lang)} totalLabel={t('crmRequests')}/>
          : <p className="empty">{t('empty')}</p>}
      </section>

      <section className="card span-8">
        <div className="card-head"><h2><Icon name="jobs" size={16}/>{t('crmOutcome')}</h2><span className="chip">14d</span></div>
        <OutcomeBars caption={t('crmOutcome')} days={outcome} okLabel={t('crmDelivered')} failLabel={t('failedShort')}/>
      </section>

      <section className="card span-4 accent">
        <div className="card-head"><h2><Icon name="arrowRight" size={16}/>{t('crmFunnel')}</h2><span className="chip">{days}d</span></div>
        <Funnel caption={t('crmFunnel')} steps={[{label: t('crmLinks'), value: funnel.links}, {label: t('crmStarted'), value: funnel.downloads},
          {label: t('crmDelivered'), value: funnel.delivered}]}/>
      </section>

      <section className="card span-7">
        <div className="card-head"><div><h2><Icon name="clock" size={16}/>{t('crmHeat')}</h2><p className="hint">{t('crmHeatHint')}</p></div><span className="chip">UTC · {days}d</span></div>
        <Heatmap caption={t('crmHeat')} grid={s.heatmap ?? Array.from({length: 7}, () => Array(24).fill(0))} days={weekdays}/>
      </section>

      <section className="card span-5">
        <div className="card-head"><h2><Icon name="bots" size={16}/>{t('perBot')}</h2></div>
        <div className="list">{botTotals.map(({bot, c, total}) => <div className="list-row" key={bot}>
          <span className="platform-icon"><Icon name={BOT_ICONS[bot] ?? 'bots'} size={18}/></span>
          <div className="grow">
            <strong>{bot}</strong>
            <small>{t('completed')}: {c.completed ?? 0} · {t('failed')}: {c.failed ?? 0} · {t('queued')}: {(c.queued ?? 0) + (c.processing ?? 0)}</small>
            <Progress value={total} max={maxBot} color="var(--chart-1)"/>
          </div>
        </div>)}{botTotals.length === 0 && <p className="empty">{t('empty')}</p>}</div>
      </section>

      <section className="card span-12">
        <div className="card-head"><h2><Icon name="check" size={16}/>{t('compatibility')}</h2><span className="chip">yt-dlp</span></div>
        <div className="compat-grid">{compat.data.map(item => <div className="compat" key={item.platform}>
          <div><strong>{sourceTitle(item.platform)}</strong><small title={item.limitations}>{item.limitations}</small></div>
          <div className="compat-meta">
            <span className={'badge compat-' + item.status.toLowerCase().replace(/ /g, '-')}>{t(item.status)}</span>
            <small>{dateTime(item.last_test_date, lang)}</small>
          </div>
        </div>)}</div>
      </section>

      <section className="card span-12">
        <div className="card-head"><div><h2><Icon name="guide" size={16}/>{t('guideTitle')}</h2><p className="hint">{t('guideSub')}</p></div>
          <button onClick={() => onNavigate('guide')}>{t('openGuide')} <Icon name="arrowRight" size={16}/></button></div>
        <BotGuideCards revision={revision}/>
      </section>
    </div>
  </div>;
}
