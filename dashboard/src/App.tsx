import {useEffect, useMemo, useState} from 'react';
import {api, setUnauthorizedHandler} from './services/api';
import {I18n, LANGS, makeT, rtl, type Lang} from './services/i18n';
import {Sidebar, type Page} from './components/Sidebar';
import {Icon} from './components/Icon';
import {LanguageSelect} from './components/ui';
import {Login} from './pages/Login';
import {Overview} from './pages/Overview';
import {Reports} from './pages/Reports';
import {Bots} from './pages/Bots';
import {Users} from './pages/Users';
import {Jobs} from './pages/Jobs';
import {Files} from './pages/Files';
import {Settings} from './pages/Settings';
import {Monetization} from './pages/Monetization';
import {Ads} from './pages/Ads';
import {Channel} from './pages/Channel';
import {Payments} from './pages/Payments';
import {Guide} from './pages/Guide';
import {Team} from './pages/Team';
import {Access, PAGE_PERMISSION, makeCan, type AccessInfo} from './services/access';

type Theme = 'dark' | 'light';
const HINTS: Partial<Record<Page, string>> = {reports: 'reportsHint', jobs: 'jobHint', files: 'fileHint', bots: 'credentialHint', guide: 'guideTitle', monetization: 'monetizationHint', ads: 'adsPageHint', channel: 'channelPageHint', payments: 'paymentsHint', team: 'teamHint'};

function stored<T extends string>(key: string, allowed: T[], fallback: T): T {
  try { const v = localStorage.getItem(key); if (v && (allowed as string[]).includes(v)) return v as T; } catch {}
  return fallback;
}
function remember(key: string, value: string) { try { localStorage.setItem(key, value); } catch {} }

export function App() {
  const [lang, setLang] = useState<Lang>(() => stored('language', [...LANGS], 'en'));
  const [theme, setTheme] = useState<Theme>(() => stored('theme', ['dark', 'light'], 'dark'));
  const value = useMemo(() => ({lang, t: makeT(lang)}), [lang]);
  const {t} = value;
  const [user, setUser] = useState<string | null>(null), [boot, setBoot] = useState(true);
  const [page, setPage] = useState<Page>('overview'), [revision, setRevision] = useState(0);
  const [userFilter, setUserFilter] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [access, setAccess] = useState<AccessInfo>({role: '', permissions: []});
  const accessValue = useMemo(() => ({role: access.role, can: makeCan(access.permissions)}), [access]);

  // Role and permissions come with /admin/me; they are loaded again after every sign-in.
  const loadMe = () => api('admin/me').then(d => { setAccess({role: d.role, permissions: d.permissions ?? []}); setUser(d.username); });
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    loadMe().catch(() => {}).finally(() => setBoot(false));
  }, []);
  useEffect(() => {  // a page the role cannot open (e.g. after a role change) falls back to the overview
    if (user && !accessValue.can(PAGE_PERMISSION[page])) setPage('overview');
  }, [user, accessValue, page]);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = rtl(lang) ? 'rtl' : 'ltr';
    remember('language', lang);
  }, [lang]);
  useEffect(() => { document.documentElement.dataset.theme = theme; remember('theme', theme); }, [theme]);
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [menuOpen]);

  const go = (p: Page) => { setPage(p); setUserFilter(null); setMenuOpen(false); window.scrollTo({top: 0}); };
  const themeButton = <button className="icon-btn" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title={t('toggleTheme')} aria-label={t('toggleTheme')}>
    <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18}/>
  </button>;

  let content;
  if (boot) content = <div className="boot">{t('loading')}</div>;
  else if (!user) content = <Login onLogin={name => { loadMe().catch(() => setUser(name)); }} lang={lang} setLang={setLang}/>;
  else content = <div className={'shell ' + (menuOpen ? 'menu-open' : '')}>
    <Sidebar page={page} user={user} onPage={go} onSignOut={() => api('auth/logout', 'POST').finally(() => setUser(null))}/>
    <div className="overlay" onClick={() => setMenuOpen(false)}/>
    <main className="main">
      <header className="topbar">
        <button className="icon-btn menu-btn" onClick={() => setMenuOpen(true)} aria-label={t('openMenu')} aria-expanded={menuOpen}><Icon name="menu"/></button>
        <div className="title"><h1>{t(page)}</h1><p>{t(HINTS[page] ?? 'subtitle')}</p></div>
        <span className="lang-select"><LanguageSelect lang={lang} onChange={setLang}/></span>
        {themeButton}
        <button className="icon-btn" onClick={() => setRevision(x => x + 1)} title={t('refresh')} aria-label={t('refresh')}><Icon name="refresh" size={18}/></button>
      </header>
      {page === 'overview' && <Overview revision={revision} user={user} onNavigate={go}/>}
      {page === 'reports' && <Reports revision={revision}/>}
      {page === 'bots' && <Bots revision={revision}/>}
      {page === 'users' && <Users revision={revision} onHistory={(id, target) => { setPage(target); setUserFilter(id); }}/>}
      {page === 'jobs' && <Jobs revision={revision} userId={userFilter} clearUser={() => setUserFilter(null)}/>}
      {page === 'files' && <Files revision={revision} userId={userFilter} clearUser={() => setUserFilter(null)}/>}
      {page === 'ads' && <Ads revision={revision}/>}
      {page === 'channel' && <Channel revision={revision}/>}
      {page === 'monetization' && <Monetization revision={revision}/>}
      {page === 'payments' && <Payments revision={revision}/>}
      {page === 'settings' && <Settings revision={revision} lang={lang} setLang={setLang}/>}
      {page === 'guide' && <Guide revision={revision}/>}
      {page === 'team' && <Team revision={revision}/>}
      <footer><span>AfoninWebStudio · Media Hub</span><span>v1.0</span></footer>
    </main>
  </div>;
  return <I18n.Provider value={value}><Access.Provider value={accessValue}>{content}</Access.Provider></I18n.Provider>;
}
