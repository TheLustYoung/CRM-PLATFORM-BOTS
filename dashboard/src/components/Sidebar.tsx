import {useI18n} from '../services/i18n';
import {PAGE_PERMISSION, useAccess} from '../services/access';
import {Icon} from './Icon';
import {Brand} from './Logo';

export type Page = 'overview' | 'reports' | 'bots' | 'users' | 'jobs' | 'files' | 'ads' | 'channel' | 'monetization' | 'payments' | 'settings' | 'guide' | 'team';
export const pages: Page[] = ['overview', 'reports', 'bots', 'users', 'jobs', 'files', 'ads', 'channel', 'monetization', 'payments', 'settings', 'team', 'guide'];

export function Sidebar({page, user, onPage, onSignOut}: {page: Page; user: string; onPage: (p: Page) => void; onSignOut: () => void}) {
  const {t} = useI18n();
  const {role, can} = useAccess();
  const roleName = t('role_' + role) === 'role_' + role ? t('role') : t('role_' + role);
  return <aside aria-label={t('openMenu')}>
    <Brand/>
    <div className="nav-label">{t('workspace')}</div>
    <nav>{pages.filter(p => can(PAGE_PERMISSION[p])).map(p => <button key={p} className={page === p ? 'active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => onPage(p)}>
      <Icon name={p}/>{t(p)}
    </button>)}
    </nav>
    <div className="sidebar-bottom">
      <span className="avatar">{user.slice(0, 2)}</span>
      <div className="who"><small>{roleName}</small><strong>{user}</strong></div>
      <button className="icon-btn ghost" onClick={onSignOut} title={t('signout')} aria-label={t('signout')}><Icon name="logout" size={18}/></button>
    </div>
  </aside>;
}
