import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {useAccess} from '../services/access';
import {useMutation, useResource} from '../services/useResource';
import {dateTime} from '../services/format';
import {Messages} from '../components/ui';
import {api, type Row} from '../services/api';

type Role = {id: string; name: string; permissions: string[]; builtin: boolean; accounts: number};
type TeamData = {accounts: Row[]; roles: Role[]; permissions: string[]; me: string};

const strongPassword = () => Array.from(crypto.getRandomValues(new Uint8Array(16)),
  b => 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'[b % 56]).join('');

/** Accounts, roles and permissions. The server enforces every rule; the page only hides what cannot be done. */
export function Team({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const team = useResource<TeamData>(`admin/team?r=${revision}`, {accounts: [], roles: [], permissions: [], me: ''});
  const {busy, error, notice, mutate, run} = useMutation(team.reload, t('saved'));
  const [form, setForm] = useState({username: '', password: '', role: 'support'});
  const [draft, setDraft] = useState<Role | null>(null);
  const {accounts, roles, permissions, me} = team.data;
  const byId = Object.fromEntries(roles.map(r => [r.id, r]));
  const within = (perms: string[]) => perms.every(p => can(p));  // nobody gives more than they have
  const grantable = roles.filter(r => within(r.permissions));
  const roleName = (r?: Role, id = '') => r ? (r.builtin ? t('role_' + r.id) : r.name) : id;

  const create = () => run(async () => {
    await api('admin/team/accounts', 'POST', form);
    setForm({username: '', password: '', role: form.role});
  });
  const saveRole = (r: Role) => run(async () => {
    await api(r.id === '' ? 'admin/team/roles' : 'admin/team/roles/' + r.id, r.id === '' ? 'POST' : 'PUT', {name: r.name, permissions: r.permissions});
    setDraft(null);
  });

  return <>
    <Messages error={team.error || error} notice={notice}/>
    <section className="panel settings">
      <div className="panel-title"><div><h2>{t('accounts')}</h2><p>{t('accountsHint')}</p></div></div>
      <div className="table-wrap"><table>
        <thead><tr>{['username', 'role', 'status', 'lastLogin', 'actions'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{accounts.map(a => {
          const role = byId[a.role], mine = a.id === me, locked = mine || !within(role?.permissions ?? []);
          return <tr key={a.id}>
            <td data-label=""><strong>{a.username}</strong>{mine && <span className="badge active"> {t('you')}</span>}
              {a.created_by && <small>{t('createdBy')}: {a.created_by}</small>}</td>
            <td data-label={t('role')}>{locked ? roleName(role, a.role) :
              <select value={a.role} disabled={busy} onChange={e => mutate('admin/team/accounts/' + a.id, 'PATCH', {role: e.target.value})}>
                {grantable.map(r => <option key={r.id} value={r.id}>{roleName(r)}</option>)}
              </select>}</td>
            <td data-label={t('status')}><span className={'badge ' + (a.active ? 'active' : 'failed')}>{a.active ? t('active') : t('blocked')}</span></td>
            <td data-label={t('lastLogin')}>{a.last_login_at ? dateTime(a.last_login_at, lang) : t('never')}</td>
            <td data-label={t('actions')}>{!locked && <div className="row-actions">
              <button disabled={busy} onClick={() => { const p = prompt(t('passwordPrompt'), strongPassword()); if (p) mutate('admin/team/accounts/' + a.id, 'PATCH', {password: p}); }}>{t('newPassword')}</button>
              <button disabled={busy} onClick={() => mutate('admin/team/accounts/' + a.id, 'PATCH', {active: !a.active})}>{a.active ? t('block') : t('unblock')}</button>
              <button className="danger" disabled={busy} onClick={() => confirm(t('confirmDeleteAccount')) && mutate('admin/team/accounts/' + a.id, 'DELETE')}>{t('deleteAccount')}</button>
            </div>}</td>
          </tr>;
        })}</tbody>
      </table></div>
    </section>

    <section className="panel settings">
      <div className="panel-title"><div><h2>{t('newAccount')}</h2><p>{t('passwordHint')}</p></div></div>
      <form className="fields" autoComplete="off" onSubmit={e => { e.preventDefault(); create(); }}>
        <label>{t('username')}<input required minLength={2} maxLength={56} pattern="[A-Za-z0-9_.\-]+" autoComplete="off"
          value={form.username} onChange={e => setForm({...form, username: e.target.value})}/></label>
        <label>{t('role')}<select value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
          {grantable.map(r => <option key={r.id} value={r.id}>{roleName(r)}</option>)}</select></label>
        <label>{t('password')}<span className="inline">
          <input required minLength={12} autoComplete="new-password" spellCheck={false} value={form.password} onChange={e => setForm({...form, password: e.target.value})}/>
          <button type="button" onClick={() => setForm({...form, password: strongPassword()})}>{t('generate')}</button></span></label>
        <div className="row-actions"><button className="primary" disabled={busy}>{t('createAccount')}</button></div>
      </form>
    </section>

    <section className="panel settings">
      <div className="panel-title"><div><h2>{t('rolesTitle')}</h2><p>{t('rolesHint')}</p></div>
        <button disabled={busy || !!draft} onClick={() => setDraft({id: '', name: '', permissions: [], builtin: false, accounts: 0})}>+ {t('newRole')}</button></div>
      <div className="bot-grid">{[...roles, ...(draft && draft.id === '' ? [draft] : [])].map(r => {
        const editing = draft && draft.id === r.id ? draft : null;
        const shown = editing ?? r, readOnly = r.builtin || !within(r.permissions);
        return <div className="panel role-card" key={r.id || 'new'}>
          <div className="panel-title"><strong>{roleName(r) || t('newRole')}</strong>
            <span>{r.builtin && <span className="badge">{t('builtinRole')}</span>} <span className="badge">{t('accountsCount').replace('{count}', String(r.accounts))}</span></span></div>
          {editing && <label>{t('roleName')}<input maxLength={64} value={editing.name} onChange={e => setDraft({...editing, name: e.target.value})}/></label>}
          <ul className="perm-list">{permissions.map(p => <li key={p}><label className="checkbox">
            <input type="checkbox" checked={shown.permissions.includes(p)} disabled={!editing || !can(p)}
              onChange={e => editing && setDraft({...editing, permissions: e.target.checked ? [...editing.permissions, p] : editing.permissions.filter(x => x !== p)})}/>
            {t('perm_' + p)}</label></li>)}</ul>
          {!readOnly && <div className="row-actions">
            {editing ? <>
              <button className="primary" disabled={busy} onClick={() => saveRole(editing)}>{t('save')}</button>
              <button onClick={() => setDraft(null)}>{t('discard')}</button>
            </> : <>
              <button disabled={busy || !!draft} onClick={() => setDraft({...r})}>{t('edit')}</button>
              <button className="danger" disabled={busy} onClick={() => mutate('admin/team/roles/' + r.id, 'DELETE')}>{t('deleteRole')}</button>
            </>}
          </div>}
        </div>;
      })}</div>
    </section>
  </>;
}
