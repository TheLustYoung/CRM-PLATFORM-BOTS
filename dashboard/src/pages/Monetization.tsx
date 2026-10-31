import {useEffect, useState, type ReactNode} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {useAccess} from '../services/access';
import {dateTime, number} from '../services/format';
import {Empty, Messages} from '../components/ui';
import {Icon} from '../components/Icon';
import {api, type Row} from '../services/api';
import {BOT_KINDS, SOURCES, sourceTitle} from '../services/sources';

type Plan = {tier?: string; days: number; stars: number; usd?: number | null; recurring?: boolean; enabled?: boolean; title?: string; badge?: string; discount?: number};
type Ad = {id?: string; text: string; button: string; url: string; enabled: boolean; bots?: string[]; languages?: string[];
  weight?: number; max_views?: number};
const BOTS = BOT_KINDS;
type Money = {
  premium_enabled: boolean; plans: Plan[]; invoice_photo_url?: string; free_max_height: number; free_max_mb: number;
  referrals_enabled: boolean; referral_invites: number; referral_days: number; referral_credits?: number;
  channel_enabled: boolean; channel: string; channel_link: string; channel_skip_premium: boolean;
  extra_channels: {chat: string; link: string}[];
  ads_enabled: boolean; ads: Ad[]; ads_every?: number; free_storage_mb?: number; tiers?: Tier[];
  free_platforms?: string[];
};
type Tier = {key: string; name: string; daily_jobs: number; max_mb: number; max_height: number; storage_mb: number; priority: boolean; no_ads: boolean;
  platforms?: string[]};

const STAR_PAYOUT_USD = 0.013;  // what a developer receives per Star when withdrawing (Telegram's reward rate)
const QUALITIES = [0, 360, 480, 720, 1080, 1440];

function Switch({checked, onChange, label}: {checked: boolean; onChange: (v: boolean) => void; label: string}) {
  return <label className="switch" title={label}>
    <input type="checkbox" role="switch" checked={checked} onChange={e => onChange(e.target.checked)} aria-label={label}/>
    <span aria-hidden="true"/>
  </label>;
}

const ALL_PLATFORMS = SOURCES;

/** Platforms included in a plan; all ticked = every platform (stored as an empty list). */
function PlatformChoice({value, onChange}: {value: string[]; onChange: (v: string[]) => void}) {
  const {t} = useI18n();
  return <fieldset><legend>{t('tierPlatforms')}</legend>{ALL_PLATFORMS.map(p => <label className="checkbox" key={p}>
    <input type="checkbox" checked={!value.length || value.includes(p)} onChange={e => {
      const current = value.length ? value : ALL_PLATFORMS;
      const next = e.target.checked ? [...current, p] : current.filter(x => x !== p);
      onChange(next.length === ALL_PLATFORMS.length ? [] : next);
    }}/>{sourceTitle(p)}</label>)}</fieldset>;
}

function Section({title, hint, icon, enabled, onToggle, children}: {
  title: string; hint: string; icon: string; enabled?: boolean; onToggle?: (v: boolean) => void; children: ReactNode;
}) {
  const {t} = useI18n();
  return <section className={'panel settings money-section' + (enabled === false ? ' is-off' : '')}>
    <div className="panel-title">
      <div className="money-head"><span className="stat-icon"><Icon name={icon} size={16}/></span><div><h2>{title}</h2><p>{hint}</p></div></div>
      {onToggle && <div className="money-toggle"><small>{t(enabled ? 'on' : 'off')}</small><Switch checked={!!enabled} onChange={onToggle} label={title}/></div>}
    </div>
    <div className="money-body">{children}</div>
  </section>;
}

export function Monetization({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const saved = useResource<Money | null>(`admin/monetization?r=${revision}`, null);
  const stats = useResource<Row>(`admin/monetization/stats?r=${revision}`, {});
  const [form, setForm] = useState<Money | null>(null);
  const [checks, setChecks] = useState<Row[] | null>(null);
  const policy = useResource<Row>(`admin/settings?r=${revision}`, {});  // free downloads per day live in the shared limits
  const [dailyJobs, setDailyJobs] = useState<number | null>(null);
  const {busy, error, notice, run} = useMutation(() => { saved.reload(); stats.reload(); policy.reload(); }, t('saved'));
  useEffect(() => { if (saved.data) setForm(saved.data); }, [saved.data]);
  useEffect(() => { if (policy.data.daily_jobs !== undefined) setDailyJobs(policy.data.daily_jobs); }, [policy.data]);

  if (!form) return <><Messages error={saved.error}/>{!saved.error && <p className="loading">{t('loading')}</p>}</>;
  const set = (patch: Partial<Money>) => setForm({...form, ...patch});
  const dailyChanged = dailyJobs !== null && dailyJobs !== policy.data.daily_jobs;
  const dirty = JSON.stringify(form) !== JSON.stringify(saved.data) || dailyChanged;
  const submit = () => run(async () => {
    await api('admin/monetization', 'PUT', form);
    if (dailyChanged) { const {languages, ...limits} = policy.data; await api('admin/settings', 'PATCH', {...limits, daily_jobs: dailyJobs}); }
  });
  const setPlan = (i: number, patch: Partial<Plan>) => set({plans: form.plans.map((p, k) => k === i ? {...p, ...patch} : p)});
  const setTier = (i: number, patch: Partial<Tier>) => set({tiers: (form.tiers ?? []).map((x, k) => k === i ? {...x, ...patch} : x)});
  const setAd = (i: number, patch: Partial<Ad>) => set({ads: form.ads.map((a, k) => k === i ? {...a, ...patch} : a)});
  const s = stats.data;
  const views: Record<string, number> = s.ad_views ?? {};
  const clicks: Record<string, number> = s.ad_clicks ?? {};
  const kpis = [
    {label: 'starsEarned30', value: s.stars_30d, icon: 'star', sub: t('purchases').replace('{count}', number(s.purchases_30d ?? 0, lang))},
    {label: 'starsTotal', value: s.stars_total, icon: 'star', sub: `≈ $${((s.stars_total ?? 0) * STAR_PAYOUT_USD).toFixed(2)}`},
    {label: 'premiumUsers', value: s.premium_users, icon: 'users'},
    {label: 'invitedUsers', value: s.invited_users, icon: 'userPlus', sub: t('rewardsGiven').replace('{count}', number(s.referral_rewards ?? 0, lang))},
  ];

  return <form className="grid money" onSubmit={e => { e.preventDefault(); submit(); }}>
    <div className="stats">{kpis.map(k => <article key={k.label} className="stat">
      <div className="stat-head"><span className="stat-label">{t(k.label)}</span><span className="stat-icon"><Icon name={k.icon} size={16}/></span></div>
      <strong>{k.value === undefined ? '—' : number(k.value, lang)}</strong>
      {k.sub && <small className="stat-sub">{k.sub}</small>}
    </article>)}</div>

    <Section title={t('premiumSection')} hint={t('premiumHint')} icon="star" enabled={form.premium_enabled} onToggle={v => set({premium_enabled: v})}>
      <div className="money-group">
        <h3>{t('tiers')}</h3>
        <p className="note">{t('tiersHint')}</p>
        <div className="plan-cards">{(form.tiers ?? []).map((tier, i) => <article className="plan-card" key={i}>
          <div className="plan-card-head">
            <strong>{tier.name}</strong><code>{tier.key}</code>
            {tier.key !== 'premium' && <button type="button" className="ghost icon-btn" aria-label={t('remove')} title={t('remove')}
              onClick={() => set({tiers: form.tiers!.filter((_, k) => k !== i), plans: form.plans.filter(p => (p.tier ?? 'premium') !== tier.key)})}><Icon name="close" size={16}/></button>}
          </div>
          <div className="plan-fields">
            <label>{t('tierName')}<input maxLength={32} required value={tier.name} onChange={e => setTier(i, {name: e.target.value})}/></label>
            <label>{t('tierDaily')}<input type="number" min={0} value={tier.daily_jobs} onChange={e => setTier(i, {daily_jobs: Number(e.target.value)})}/></label>
            <label>{t('tierMaxMb')}<input type="number" min={0} max={2000} value={tier.max_mb} onChange={e => setTier(i, {max_mb: Number(e.target.value)})}/></label>
            <label>{t('freeMaxHeight')}<select value={tier.max_height} onChange={e => setTier(i, {max_height: Number(e.target.value)})}>
              {[0, 720, 1080, 1440, 2160].map(q => <option key={q} value={q}>{q ? `${q}p` : t('anyQuality')}</option>)}</select></label>
            <label>{t('tierStorageMb')}<input type="number" min={0} value={tier.storage_mb} onChange={e => setTier(i, {storage_mb: Number(e.target.value)})}/></label>
          </div>
          <label className="checkbox"><input type="checkbox" checked={tier.priority} onChange={e => setTier(i, {priority: e.target.checked})}/>{t('tierPriority')}</label>
          <label className="checkbox"><input type="checkbox" checked={tier.no_ads} onChange={e => setTier(i, {no_ads: e.target.checked})}/>{t('tierNoAds')}</label>
          <PlatformChoice value={tier.platforms ?? []} onChange={platforms => setTier(i, {platforms})}/>
        </article>)}</div>
        {(form.tiers ?? []).length < 6 && <button type="button" onClick={() => {
          const key = prompt(t('tierKeyPrompt'))?.trim().toLowerCase();
          if (key && /^[a-z0-9_-]{1,24}$/.test(key) && !(form.tiers ?? []).some(x => x.key === key))
            set({tiers: [...(form.tiers ?? []), {key, name: key[0].toUpperCase() + key.slice(1), daily_jobs: 0, max_mb: 0, max_height: 0, storage_mb: 0, priority: true, no_ads: true}]});
        }}>+ {t('addTier')}</button>}
      </div>
      <div className="money-group">
        <h3>{t('plans')}</h3>
        <p className="note">{t('starsRules')}</p>
        <div className="plan-cards">{form.plans.map((p, i) => {
          const off = (value: number) => value * (100 - (p.discount ?? 0)) / 100;
          const stars = Math.max(1, Math.round(off(p.stars)));
          return <article className={'plan-card' + (p.enabled === false ? ' is-off' : '')} key={i}>
            <div className="plan-card-head">
              <Switch checked={p.enabled !== false} onChange={v => setPlan(i, {enabled: v})} label={t('planEnabled')}/>
              <select value={p.recurring ? 'sub' : 'once'} aria-label={t('planType')}
                onChange={e => setPlan(i, e.target.value === 'sub' ? {recurring: true, days: 30} : {recurring: false})}>
                <option value="once">{t('planOnce')}</option><option value="sub">{t('planSubscription')}</option>
              </select>
              <button type="button" className="ghost icon-btn" aria-label={t('remove')} title={t('remove')}
                onClick={() => set({plans: form.plans.filter((_, k) => k !== i)})}><Icon name="close" size={16}/></button>
            </div>
            <div className="plan-fields">
              {(form.tiers ?? []).length > 1 && <label>{t('tier')}<select value={p.tier ?? 'premium'} onChange={e => setPlan(i, {tier: e.target.value})}>
                {form.tiers!.map(x => <option key={x.key} value={x.key}>{x.name}</option>)}</select></label>}
              <label>{t('planDays')}<input type="number" min={1} max={3650} required disabled={p.recurring} value={p.days}
                onChange={e => setPlan(i, {days: Number(e.target.value)})}/></label>
              <label>{t('planStars')}<input type="number" min={1} max={10000} required value={p.stars} onChange={e => setPlan(i, {stars: Number(e.target.value)})}/></label>
              <label>{t('planUsd')}<input type="number" min={0.5} max={10000} step={0.01} value={p.usd ?? ''} placeholder="—" disabled={p.recurring}
                onChange={e => setPlan(i, {usd: e.target.value ? Number(e.target.value) : null})}/></label>
              <label>{t('planDiscount')}<input type="number" min={0} max={90} value={p.discount ?? 0} onChange={e => setPlan(i, {discount: Number(e.target.value)})}/></label>
              <label>{t('planTitle')}<input maxLength={32} value={p.title ?? ''} placeholder={t('planTitlePh')} onChange={e => setPlan(i, {title: e.target.value})}/></label>
              <label>{t('planBadge')}<input maxLength={24} value={p.badge ?? ''} placeholder="🔥 Best value" onChange={e => setPlan(i, {badge: e.target.value})}/></label>
            </div>
            <div className="plan-summary">
              <strong>{p.title || (p.recurring ? t('planSubscription') : `${p.days} ${t('days').toLowerCase()}`)}</strong>
              <span>{stars} ⭐{p.recurring ? ' / 30d' : ''}{p.usd && !p.recurring ? ` · $${off(p.usd).toFixed(2)}` : ''}
                {p.discount ? <s> {p.stars} ⭐</s> : null}{p.badge ? <em> {p.badge}</em> : null}</span>
              <small>{t('payout').replace('{usd}', (stars * STAR_PAYOUT_USD).toFixed(2))}</small>
            </div>
          </article>;
        })}</div>
        {form.plans.length < 8 && <button type="button" onClick={() => set({plans: [...form.plans,
          {days: 30, stars: 100, usd: null, recurring: false, enabled: true, title: '', badge: '', discount: 0}]})}>+ {t('addPlan')}</button>}
        <label>{t('invoicePhoto')}<input type="url" value={form.invoice_photo_url ?? ''} placeholder="https://…/premium.jpg"
          onChange={e => set({invoice_photo_url: e.target.value})}/><small className="hint">{t('invoicePhotoHint')}</small></label>
      </div>
      <div className="money-group">
        <h3>{t('freeTier')}</h3>
        <div className="fields three">
          <label>{t('freeDailyJobs')}<input type="number" min={1} max={10000} required value={dailyJobs ?? ''} onChange={e => setDailyJobs(Number(e.target.value))}/></label>
          <label>{t('freeMaxHeight')}<select value={form.free_max_height} onChange={e => set({free_max_height: Number(e.target.value)})}>
            {QUALITIES.map(q => <option key={q} value={q}>{q ? `${q}p` : t('anyQuality')}</option>)}
          </select></label>
          <label>{t('freeMaxMb')}<input type="number" min={0} max={2000} required value={form.free_max_mb} onChange={e => set({free_max_mb: Number(e.target.value)})}/></label>
          <label>{t('tierStorageMb')}<input type="number" min={0} value={form.free_storage_mb ?? 0} onChange={e => set({free_storage_mb: Number(e.target.value)})}/></label>
        </div>
        <PlatformChoice value={form.free_platforms ?? []} onChange={free_platforms => set({free_platforms})}/>
      </div>
    </Section>

    <Section title={t('referralsSection')} hint={t('referralsHint')} icon="userPlus" enabled={form.referrals_enabled} onToggle={v => set({referrals_enabled: v})}>
      <div className="fields">
        <label>{t('referralInvites')}<input type="number" min={1} max={100} required value={form.referral_invites} onChange={e => set({referral_invites: Number(e.target.value)})}/></label>
        <label>{t('referralDays')}<input type="number" min={1} max={365} required value={form.referral_days} onChange={e => set({referral_days: Number(e.target.value)})}/></label>
        <label>{t('referralCredits')}<input type="number" min={0} max={10000} value={form.referral_credits ?? 0} onChange={e => set({referral_credits: Number(e.target.value)})}/></label>
      </div>
      <p className="hint">{t('referralExample').replace('{invites}', String(form.referral_invites)).replace('{days}', String(form.referral_days))}</p>
    </Section>

    <Section title={t('channelSection')} hint={t('channelHint')} icon="link" enabled={form.channel_enabled} onToggle={v => set({channel_enabled: v})}>
      <div className="fields">
        <label>{t('channelId')}<input value={form.channel} placeholder="@my_channel" spellCheck={false} onChange={e => set({channel: e.target.value})}/></label>
        <label>{t('channelLink')}<input value={form.channel_link} placeholder="https://t.me/+AbCdEf…" spellCheck={false} onChange={e => set({channel_link: e.target.value})}/></label>
      </div>
      {(form.extra_channels ?? []).map((c, i) => <div className="fields" key={i}>
        <label>{t('channelId')} {i + 2}<input value={c.chat} placeholder="@my_channel" spellCheck={false}
          onChange={e => set({extra_channels: form.extra_channels.map((x, j) => j === i ? {...x, chat: e.target.value} : x)})}/></label>
        <label>{t('channelLink')}<input value={c.link} placeholder="https://t.me/+AbCdEf…" spellCheck={false}
          onChange={e => set({extra_channels: form.extra_channels.map((x, j) => j === i ? {...x, link: e.target.value} : x)})}/></label>
        <button type="button" className="danger" onClick={() => set({extra_channels: form.extra_channels.filter((_, j) => j !== i)})}>{t('remove')}</button>
      </div>)}
      {(form.extra_channels ?? []).length < 9 &&
        <button type="button" onClick={() => set({extra_channels: [...(form.extra_channels ?? []), {chat: '', link: ''}]})}>+ {t('addChannel')}</button>}
      <p className="hint">{t('channelsHint')}</p>
      <label className="checkbox"><input type="checkbox" checked={form.channel_skip_premium} onChange={e => set({channel_skip_premium: e.target.checked})}/>{t('channelSkipPremium')}</label>
      <div className="row-actions">
        <button type="button" disabled={busy || !saved.data?.channel || dirty} title={dirty ? t('unsaved') : ''}
          onClick={() => run(async () => setChecks(await api<Row[]>('admin/monetization/channel-test', 'POST')))}>{t('checkChannel')}</button>
        {checks?.map(c => <span key={c.bot + c.chat} className={'badge ' + (c.ok ? 'active' : 'failed')} title={c.detail}>
          {c.chat} · {c.bot}: {c.ok ? t('botIsAdmin') : t('botNotAdmin')}</span>)}
      </div>
    </Section>

    <Section title={t('adsSection')} hint={t('adsHint')} icon="activity" enabled={form.ads_enabled} onToggle={v => set({ads_enabled: v})}>
      <div className="ad-list">{form.ads.map((a, i) => <div className={'ad-card' + (a.enabled ? '' : ' is-off')} key={a.id ?? 'new' + i}>
        <div className="ad-card-head">
          <label className="checkbox"><input type="checkbox" checked={a.enabled} onChange={e => setAd(i, {enabled: e.target.checked})}/>{t('adEnabled')}</label>
          {a.id && <span className="pill">{t('views').replace('{count}', number(views[a.id] ?? 0, lang))}</span>}
          {a.id && <span className="pill">{t('adClicks').replace('{count}', number(clicks[a.id] ?? 0, lang))}
            {views[a.id] ? ` · CTR ${(100 * (clicks[a.id] ?? 0) / views[a.id]).toFixed(1)}%` : ''}</span>}
          <button type="button" className="ghost icon-btn" aria-label={t('remove')} title={t('remove')} onClick={() => set({ads: form.ads.filter((_, k) => k !== i)})}><Icon name="close" size={16}/></button>
        </div>
        <label>{t('adText')}<textarea rows={2} maxLength={300} required value={a.text} onChange={e => setAd(i, {text: e.target.value})}/></label>
        <div className="fields">
          <label>{t('adButton')}<input maxLength={40} value={a.button} onChange={e => setAd(i, {button: e.target.value})}/></label>
          <label>{t('adUrl')}<input type="url" pattern="https://.*" value={a.url} placeholder="https://" onChange={e => setAd(i, {url: e.target.value})}/></label>
          <label>{t('adWeight')}<input type="number" min={1} max={100} value={a.weight ?? 1} onChange={e => setAd(i, {weight: Number(e.target.value) || 1})}/></label>
          <label>{t('adMaxViews')}<input type="number" min={0} value={a.max_views ?? 0} onChange={e => setAd(i, {max_views: Number(e.target.value) || 0})}/></label>
        </div>
        <fieldset><legend>{t('adBots')}</legend>{BOTS.map(bot => <label className="checkbox" key={bot}>
          <input type="checkbox" checked={!(a.bots ?? []).length || (a.bots ?? []).includes(bot)} onChange={e => {
            const current = (a.bots ?? []).length ? a.bots! : BOTS;
            const next = e.target.checked ? [...current, bot] : current.filter(b => b !== bot);
            setAd(i, {bots: next.length === BOTS.length ? [] : next});
          }}/>{bot}</label>)}</fieldset>
        <label>{t('adLanguages')}<input value={(a.languages ?? []).join(', ')} placeholder="en, ar, he"
          onChange={e => setAd(i, {languages: e.target.value.split(',').map(x => x.trim().toLowerCase()).filter(Boolean)})}/></label>
      </div>)}</div>
      {form.ads.length < 20 && <button type="button" onClick={() => set({ads: [...form.ads, {text: '', button: '', url: '', enabled: true, bots: [], languages: [], weight: 1, max_views: 0}]})}>+ {t('addAd')}</button>}
      <label>{t('adsEvery')}<input type="number" min={1} max={50} value={form.ads_every ?? 1} onChange={e => set({ads_every: Number(e.target.value) || 1})}/></label>
    </Section>

    {can('money.manage') ? <div className={'save-bar' + (dirty ? ' dirty' : '')}>
      <Messages error={error} notice={dirty ? '' : notice}/>
      {dirty && <span>{t('unsaved')}</span>}
      <button type="button" disabled={busy || !dirty} onClick={() => { setForm(saved.data); setDailyJobs(policy.data.daily_jobs ?? null); }}>{t('discard')}</button>
      <button className="primary" disabled={busy || !dirty}>{t('saveChanges')}</button>
    </div> : <p className="notice">{t('readOnly')}</p>}

    <section className="panel">
      <div className="panel-title"><div><h2>{t('recentPayments')}</h2><p>{t('recentPaymentsHint')}</p></div></div>
      <div className="table-wrap"><table>
        <thead><tr>{['created', 'user', 'source', 'days', 'stars'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{(s.recent ?? []).map((p: Row) => <tr key={p.id}>
          <td data-label={t('created')}>{dateTime(p.created_at, lang)}</td>
          <td data-label={t('user')}><strong>{p.username ? '@' + p.username : p.user_id}</strong></td>
          <td data-label={t('source')}><span className={'badge ' + (p.source === 'stars' ? 'active' : '')}>{t('src_' + p.source)}</span></td>
          <td data-label={t('days')}>{p.days}</td>
          <td data-label={t('stars')}>{p.stars ? `⭐ ${number(p.stars, lang)}` : '—'}</td>
        </tr>)}</tbody>
      </table></div>
      <Empty show={!stats.loading && (s.recent ?? []).length === 0}/>
    </section>
  </form>;
}
