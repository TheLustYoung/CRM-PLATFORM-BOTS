import {useEffect, useMemo, useState, type ReactNode} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {useAccess} from '../services/access';
import {dateTime, number} from '../services/format';
import {Empty, Messages, Pagination} from '../components/ui';
import {Icon} from '../components/Icon';
import {api, type Row} from '../services/api';

type Field = {key: string; label: string; secret: boolean; placeholder: string; options?: string[]; value: string | null; set: boolean; hint: string};
type Provider = {key: string; category: 'card' | 'crypto'; title: string; docs: string; implemented: boolean; ready: boolean; fields: Field[];
  webhook_url: string | null; events?: string};
type Category = {enabled: boolean; provider: string};
type Form = {stars_enabled: boolean; public_url: string; card: Category; crypto: Category};
const STATUSES = ['pending', 'paid', 'failed', 'expired', 'canceled', 'refunded'];

const money = (amount: number, currency: string, lang: string) =>
  currency === 'USD' ? new Intl.NumberFormat(lang, {style: 'currency', currency: 'USD'}).format(amount / 100) : `${number(amount, lang)} ⭐`;

function Switch({checked, onChange, label}: {checked: boolean; onChange: (v: boolean) => void; label: string}) {
  return <label className="switch" title={label}>
    <input type="checkbox" role="switch" checked={checked} onChange={e => onChange(e.target.checked)} aria-label={label}/><span aria-hidden="true"/>
  </label>;
}

function Section({title, hint, icon, enabled, onToggle, badge, children}: {
  title: string; hint: string; icon: string; enabled?: boolean; onToggle?: (v: boolean) => void; badge?: ReactNode; children?: ReactNode;
}) {
  const {t} = useI18n();
  return <section className={'panel settings money-section' + (enabled === false ? ' is-off' : '')}>
    <div className="panel-title">
      <div className="money-head"><span className="stat-icon"><Icon name={icon} size={16}/></span><div><h2>{title} {badge}</h2><p>{hint}</p></div></div>
      {onToggle && <div className="money-toggle"><small>{t(enabled ? 'on' : 'off')}</small><Switch checked={!!enabled} onChange={onToggle} label={title}/></div>}
    </div>
    {children && <div className="money-body">{children}</div>}
  </section>;
}

function Copy({value}: {value: string}) {
  const {t} = useI18n();
  const [done, setDone] = useState(false);
  return <div className="copy-field"><code>{value}</code>
    <button type="button" onClick={() => navigator.clipboard?.writeText(value).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); })}>
      {t(done ? 'copied' : 'copy')}</button></div>;
}

function status(p: Provider) {
  return !p.implemented ? 'providerPending' : p.ready ? 'configured' : 'notConfigured';
}

export function Payments({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const editable = can('money.manage');
  const [tick, setTick] = useState(0);
  const saved = useResource<Row | null>(`admin/payments?r=${revision}-${tick}`, null);
  const revenue = useResource<Row[]>(`admin/payments/revenue?r=${revision}-${tick}`, []);
  const [filter, setFilter] = useState({status: '', method: ''}), [offset, setOffset] = useState(0);
  const orders = useResource<Row[]>(`admin/payments/orders?offset=${offset}&status=${filter.status}&method=${filter.method}&r=${revision}-${tick}`, []);
  const [form, setForm] = useState<Form | null>(null);
  const [values, setValues] = useState<Record<string, Record<string, string | null>>>({});  // typed in this session
  const [checks, setChecks] = useState<Record<string, Row>>({});
  const {busy, error, notice, run} = useMutation(() => setTick(x => x + 1), t('saved'));
  const providers: Provider[] = saved.data?.providers ?? [];
  useEffect(() => {
    if (!saved.data) return;
    const d = saved.data;
    setForm({stars_enabled: d.stars_enabled, public_url: d.public_url, card: d.card, crypto: d.crypto});
    setValues({});
  }, [saved.data]);
  const initial = useMemo(() => saved.data ? JSON.stringify({stars_enabled: saved.data.stars_enabled, public_url: saved.data.public_url,
    card: saved.data.card, crypto: saved.data.crypto}) : '', [saved.data]);
  if (!form || !saved.data) return <><Messages error={saved.error}/>{!saved.error && <p className="loading">{t('loading')}</p>}</>;
  const dirty = JSON.stringify(form) !== initial || Object.keys(values).length > 0;
  const setValue = (provider: string, key: string, value: string | null) =>
    setValues({...values, [provider]: {...(values[provider] ?? {}), [key]: value}});
  const save = () => run(() => api('admin/payments', 'PUT', {...form, providers: values}));
  const methodTitle = (key: string) => key === 'stars' ? t('m_stars') : providers.find(p => p.key === key)?.title ?? key;

  const categorySection = (category: 'card' | 'crypto') => {
    const choice = form[category];
    const options = providers.filter(p => p.category === category);
    const p = options.find(o => o.key === choice.provider) ?? options[0];
    const check = checks[p.key];
    return <Section key={category} title={t(category === 'card' ? 'cardPayments' : 'cryptoPayments')}
      hint={t(category === 'card' ? 'cardHint' : 'cryptoHint')} icon={category === 'card' ? 'shield' : 'link'}
      enabled={choice.enabled} onToggle={v => setForm({...form, [category]: {...choice, enabled: v}})}
      badge={<span className={'badge ' + (status(p) === 'configured' ? 'active' : 'offline')}>{t(status(p))}</span>}>
      <label>{t('provider')}<select value={p.key} onChange={e => setForm({...form, [category]: {...choice, provider: e.target.value}})}>
        {options.map(o => <option key={o.key} value={o.key}>{o.title}{o.implemented ? '' : ` — ${t('providerPendingShort')}`}</option>)}
      </select></label>
      {!p.implemented && <p className="note">{t('providerPendingHint')}</p>}
      {choice.enabled && !p.ready && <p className="hint">{t('soonInBots')}</p>}
      <p className="hint"><a href={p.docs} target="_blank" rel="noreferrer">{t('whereKeys').replace('{name}', p.title)} ↗</a></p>
      <div className="fields">{p.fields.map(f => {
        const typed = values[p.key]?.[f.key];
        if (f.options) return <label key={f.key}>{f.label}
          <select value={typed ?? f.value ?? f.options[0]} onChange={e => setValue(p.key, f.key, e.target.value)}>
            {f.options.map(o => <option key={o} value={o}>{o}</option>)}</select></label>;
        return <label key={f.key}>{f.label}
          <div className="inline"><input type={f.secret ? 'password' : 'text'} autoComplete="off" spellCheck={false}
            value={typed ?? (f.secret ? '' : f.value ?? '')} placeholder={f.secret && f.set ? f.hint : f.placeholder}
            onChange={e => setValue(p.key, f.key, f.secret && !e.target.value ? null : e.target.value)}/>
            {f.secret && f.set && <button type="button" className="ghost" onClick={() => setValue(p.key, f.key, '')}>{t('removeKeyShort')}</button>}</div>
          {f.secret && f.set && typed !== '' && <small className="hint">{t('keySaved').replace('{hint}', f.hint)}</small>}
          {typed === '' && <small className="hint">{t('willRemove')}</small>}
        </label>;
      })}</div>
      {p.webhook_url && <label>{t('webhookUrl')}<Copy value={p.webhook_url}/>
        {p.events && <small className="hint">{t('webhookEvents').replace('{events}', p.events)}</small>}</label>}
      <div className="row-actions">
        {editable && <button type="button" disabled={busy || dirty} title={dirty ? t('unsaved') : ''}
          onClick={() => run(async () => setChecks({...checks, [p.key]: await api<Row>(`admin/payments/${p.key}/test`, 'POST')}))}>{t('testProxies')}</button>}
        {check && <span className={'badge ' + (check.ok ? 'active' : 'failed')}>{check.detail}</span>}
      </div>
    </Section>;
  };

  return <div className="grid money payments">
    <section className="panel">
      <div className="panel-title"><div><h2>{t('revenue')}</h2><p>{t('revenueHint')}</p></div></div>
      <div className="table-wrap"><table>
        <thead><tr>{['method', 'today', 'd7', 'd30', 'allTime'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{revenue.data.map(r => <tr key={r.method + r.currency}>
          <td data-label=""><strong>{methodTitle(r.method)}</strong></td>
          {['today', 'd7', 'd30', 'all'].map(period => <td key={period} data-label={t(period === 'all' ? 'allTime' : period)}>
            {money(r[period], r.currency, lang)}<small>{t('ordersCount').replace('{count}', number(r[`${period}_count`], lang))}</small></td>)}
        </tr>)}</tbody>
      </table></div>
      <Empty show={!revenue.loading && revenue.data.length === 0}/>
    </section>

    <Section title={t('publicDomain')} hint={t('publicDomainHint')} icon="globe">
      <label>{t('publicDomain')}<input value={form.public_url} placeholder="https://pay.example.com" spellCheck={false}
        onChange={e => setForm({...form, public_url: e.target.value})}/></label>
      <p className="hint">{t('currentBase').replace('{url}', saved.data.base_url)}</p>
    </Section>

    <Section title={t('m_stars')} hint={t('starsHint')} icon="star" enabled={form.stars_enabled} onToggle={v => setForm({...form, stars_enabled: v})}/>
    {categorySection('card')}
    {categorySection('crypto')}
    <p className="hint pad-x">{t('priceUsdHint')}</p>

    {editable ? <div className={'save-bar' + (dirty ? ' dirty' : '')}>
      <Messages error={error} notice={dirty ? '' : notice}/>
      {dirty && <span>{t('unsaved')}</span>}
      <button type="button" disabled={busy || !dirty} onClick={() => setTick(x => x + 1)}>{t('discard')}</button>
      <button type="button" className="primary" disabled={busy || !dirty} onClick={save}>{t('saveChanges')}</button>
    </div> : <p className="notice">{t('readOnly')}</p>}

    <section className="panel">
      <div className="panel-title"><div><h2>{t('transactions')}</h2></div></div>
      <div className="filters">
        <select value={filter.status} onChange={e => { setFilter({...filter, status: e.target.value}); setOffset(0); }} aria-label={t('status')}>
          <option value="">{t('allStatuses')}</option>{STATUSES.map(x => <option key={x} value={x}>{t('os_' + x)}</option>)}
        </select>
        <select value={filter.method} onChange={e => { setFilter({...filter, method: e.target.value}); setOffset(0); }} aria-label={t('method')}>
          <option value="">{t('allMethods')}</option>
          {['stars', ...providers.map(p => p.key)].map(x => <option key={x} value={x}>{methodTitle(x)}</option>)}
        </select>
      </div>
      <div className="table-wrap"><table>
        <thead><tr>{['created', 'user', 'method', 'amount', 'days', 'status', 'actions'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{orders.data.map(o => <tr key={o.id}>
          <td data-label={t('created')}>{dateTime(o.paid_at ?? o.created_at, lang)}</td>
          <td data-label={t('user')}><strong>{o.username ? '@' + o.username : o.user_id}</strong></td>
          <td data-label={t('method')}>{methodTitle(o.method)}</td>
          <td data-label={t('amount')}>{o.amount != null ? money(o.amount, o.currency, lang) : '—'}</td>
          <td data-label={t('days')}>{o.days}</td>
          <td data-label={t('status')}><span className={'badge order-' + o.status}>{t('os_' + o.status)}</span></td>
          <td data-label={t('actions')}>{o.status === 'paid' && editable && <button className="danger" disabled={busy}
            onClick={() => confirm(t('confirmRefund')) && run(() => api(`admin/payments/orders/${o.id}/refund`, 'POST'))}>{t('refund')}</button>}</td>
        </tr>)}</tbody>
      </table></div>
      <Empty show={!orders.loading && orders.data.length === 0}/>
      <Pagination offset={offset} count={orders.data.length} onChange={setOffset}/>
    </section>
  </div>;
}
