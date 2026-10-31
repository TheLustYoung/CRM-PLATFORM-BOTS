import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {useAccess} from '../services/access';
import {dateTime, number} from '../services/format';
import {Badge, Empty, LimitForm, Messages, Pagination} from '../components/ui';
import type {Row} from '../services/api';

const isPremium = (u: Row) => !!u.premium_until && new Date(u.premium_until) > new Date();

/** Gift Premium days to a user (support, partners, giveaways) or take it away. */
function PremiumControl({user, busy, onGrant}: {user: Row; busy: boolean; onGrant: (days: number, tier: string) => void}) {
  const {t, lang} = useI18n();
  const [days, setDays] = useState(30);
  const money = useResource<Row | null>('admin/monetization', null);
  const tiers: Row[] = money.data?.tiers ?? [{key: 'premium', name: 'Premium'}];
  const [tier, setTier] = useState('premium');
  const current = tiers.find(x => x.key === (user.premium_tier || 'premium'));
  return <div className="pad premium-control">
    <p className="cookies-status">
      <span className={'badge ' + (isPremium(user) ? 'premium-badge' : '')}>{isPremium(user) ? '⭐ ' + (current?.name ?? t('premium')) : t('free')}</span>
      {isPremium(user) && <>{t('premiumUntil')}: {dateTime(user.premium_until, lang)}</>}
    </p>
    <form className="inline" onSubmit={e => { e.preventDefault(); if (days > 0) onGrant(days, tier); }}>
      {tiers.length > 1 && <select aria-label={t('tier')} value={tier} onChange={e => setTier(e.target.value)}>
        {tiers.map(x => <option key={x.key} value={x.key}>{x.name}</option>)}</select>}
      <input type="number" min={1} max={3650} value={days} aria-label={t('grantDays')} onChange={e => setDays(Number(e.target.value))}/>
      <button disabled={busy}>⭐ {t('grantPremium')}</button>
      {isPremium(user) && <button type="button" className="danger" disabled={busy} onClick={() => confirm(t('confirmRemovePremium')) && onGrant(0, tier)}>{t('removePremium')}</button>}
    </form>
  </div>;
}

export function Users({revision, onHistory}: {revision: number; onHistory: (userId: number, page: 'jobs' | 'files') => void}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const [search, setSearch] = useState(''), [query, setQuery] = useState(''), [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const list = useResource<Row[]>(`admin/users?offset=${offset}&q=${encodeURIComponent(query)}&r=${revision}`, []);
  const detail = useResource<Row>(selected ? `admin/users/${selected}?r=${revision}` : null, {});
  const {busy, error, notice, mutate} = useMutation(() => { list.reload(); detail.reload(); }, t('saved'));
  const d = detail.data;
  return <>
    <Messages error={list.error || error} notice={notice}/>
    {selected && d.id && <section className="panel drawer">
      <div className="panel-title"><div><h2>{d.username ? '@' + d.username : d.id}</h2><p>{d.first_name ?? ''} · ID {d.id}</p></div>
        <button onClick={() => setSelected(null)}>{t('close')} ✕</button></div>
      <dl className="mini-stats wide">
        <div><dt>{t('language')}</dt><dd>{d.language}</dd></div>
        <div><dt>{t('bots_list')}</dt><dd>{(d.bots ?? []).join(', ') || '—'}</dd></div>
        <div><dt>{t('downloadsCount')}</dt><dd>{number(d.downloads, lang)}</dd></div>
        <div><dt>{t('uploadsCount')}</dt><dd>{number(d.uploads, lang)}</dd></div>
        <div><dt>{t('failedCount')}</dt><dd>{number(d.failed, lang)}</dd></div>
        <div><dt>{t('filesActive')}</dt><dd>{number(d.files, lang)}</dd></div>
        <div><dt>{t('joined')}</dt><dd>{dateTime(d.created_at, lang)}</dd></div>
        <div><dt>{t('lastSeen')}</dt><dd>{dateTime(d.last_seen, lang)}</dd></div>
      </dl>
      {(d.payments ?? []).length > 0 && <div className="pad table-wrap"><table>
        <thead><tr>{['created', 'paymentSource', 'days', 'stars', 'bot'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{d.payments.map((p: Row, i: number) => <tr key={i}>
          <td data-label={t('created')}>{dateTime(p.created_at, lang)}</td><td data-label={t('paymentSource')}>{p.source}</td>
          <td data-label={t('days')}>{p.days}</td><td data-label={t('stars')}>{p.stars || '—'}</td><td data-label={t('bot')}>{p.bot_id ?? '—'}</td>
        </tr>)}</tbody></table></div>}
      {can('money.manage') && <PremiumControl user={d} busy={busy} onGrant={(days, tier) => mutate(`admin/users/${d.id}/premium`, 'POST', {days, tier})}/>}
      {can('users.manage') && <div className="pad">
        <form className="inline" onSubmit={e => {
          e.preventDefault();
          const credits = Number(new FormData(e.currentTarget).get('credits'));
          if (credits >= 0) mutate('admin/users/' + d.id, 'PATCH', {banned: d.banned, daily_limit: d.daily_limit, credits});
        }}>
          <label>{t('credits')} <small>{t('creditsHint')}</small>
            <input key={d.credits} type="number" name="credits" min={0} max={1000000} defaultValue={d.credits ?? 0}/></label>
          <button disabled={busy}>✓</button>
        </form></div>}
      <div className="row-actions pad">
        <button onClick={() => onHistory(d.id, 'jobs')}>{t('jobs_of_user')} →</button>
        <button onClick={() => onHistory(d.id, 'files')}>{t('files_of_user')} →</button>
      </div>
    </section>}
    <section className="panel">
      <form className="search" onSubmit={e => { e.preventDefault(); setQuery(search); setOffset(0); }}>
        <input placeholder={t('search')} aria-label={t('search')} value={search} onChange={e => setSearch(e.target.value)}/>
        <button className="primary">{t('searchButton')}</button>
      </form>
      <div className="table-wrap"><table>
        <thead><tr>{['user', 'status', 'dailyLimit', 'lastSeen', 'actions'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{list.data.map(u => <tr key={u.id}>
          <td data-label=""><strong>{u.username ? '@' + u.username : u.first_name || u.id}</strong><small>{u.id}</small></td>
          <td data-label={t('status')}><div className="badges"><Badge status={u.banned ? 'disabled' : 'enabled'}/>
            {isPremium(u) && <span className="badge premium-badge" title={dateTime(u.premium_until, lang)}>⭐ {t('premium')}</span>}</div></td>
          <td data-label={t('dailyLimit')}>{can('users.manage')
            ? <LimitForm value={u.daily_limit} label={t('dailyLimit')} busy={busy} onSave={v => mutate('admin/users/' + u.id, 'PATCH', {banned: u.banned, daily_limit: v})}/>
            : (u.daily_limit ?? '—')}</td>
          <td data-label={t('lastSeen')}>{dateTime(u.last_seen, lang)}</td>
          <td data-label={t('actions')}><div className="row-actions">
            {can('users.manage') && <button disabled={busy} className={u.banned ? '' : 'danger'} onClick={() => mutate('admin/users/' + u.id, 'PATCH', {banned: !u.banned, daily_limit: u.daily_limit})}>{t(u.banned ? 'unban' : 'ban')}</button>}
            <button onClick={() => setSelected(u.id)}>{t('details')} →</button>
          </div></td>
        </tr>)}</tbody>
      </table></div>
    </section>
    <Empty show={!list.loading && list.data.length === 0}/>
    <Pagination offset={offset} count={list.data.length} onChange={setOffset}/>
  </>;
}
