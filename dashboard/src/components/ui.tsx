import React from 'react';
import {useI18n, isLang, languageNames, type Lang} from '../services/i18n';
import {Flag} from './Flag';

export function Badge({status}: {status: string}) {
  const {t} = useI18n();
  return <span className={'badge ' + status}>{t(status)}</span>;
}

export function StatCard({label, value, icon, featured}: {label: string; value: React.ReactNode; icon: string; featured?: boolean}) {
  return <article className={'stat ' + (featured ? 'featured' : '')}><span>{label}</span><strong>{value}</strong><i>{icon}</i></article>;
}

export function Pagination({offset, count, onChange}: {offset: number; count: number; onChange: (offset: number) => void}) {
  const {t} = useI18n();
  return <div className="pagination">
    <button disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - 50))}>{t('previous')}</button>
    <span>{count ? offset + 1 : 0}–{offset + count}</span>
    <button disabled={count < 50} onClick={() => onChange(offset + 50)}>{t('next')}</button>
  </div>;
}

export function LimitForm({value, label, busy, onSave}: {value: number | null; label: string; busy: boolean; onSave: (value: number) => void}) {
  const {t} = useI18n();
  return <form className="inline" onSubmit={e => {
    e.preventDefault();
    const v = Number(new FormData(e.currentTarget).get('limit'));
    if (v > 0) onSave(v);
  }}>
    <input aria-label={label} type="number" name="limit" defaultValue={value ?? 20} min="1" max="100000" required/>
    <button disabled={busy} aria-label={t('save')}>✓</button>
  </form>;
}

/** Language menu with a flag next to every language. `names` maps codes to labels (defaults to the dashboard's languages). */
export function LanguagePicker({value, onChange, names, label}: {
  value: string; onChange: (code: string) => void; names?: Record<string, string>; label?: string;
}) {
  const {t} = useI18n();
  const items: Record<string, string> = names ?? languageNames;
  const [open, setOpen] = React.useState(false);
  const root = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', outside);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('mousedown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  const pick = (code: string) => { setOpen(false); if (code !== value) onChange(code); };
  return <div className="lang-picker" ref={root}>
    <button type="button" className="lang-current" aria-haspopup="listbox" aria-expanded={open} aria-label={label ?? t('language')} onClick={() => setOpen(!open)}>
      <Flag code={value}/><span>{items[value] ?? value}</span><svg className="chevron" width={12} height={12} viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2}/></svg>
    </button>
    {open && <ul className="lang-menu" role="listbox" aria-label={label ?? t('language')}>
      {Object.entries(items).map(([code, name]) => <li key={code} role="option" aria-selected={code === value}>
        <button type="button" lang={code} onClick={() => pick(code)} className={code === value ? 'active' : ''}>
          <Flag code={code}/><span>{name}</span>{code === value && <span className="lang-check" aria-hidden="true">✓</span>}
        </button>
      </li>)}
    </ul>}
  </div>;
}

export function LanguageSelect({lang, onChange}: {lang: Lang; onChange: (lang: Lang) => void}) {
  return <LanguagePicker value={lang} onChange={code => isLang(code) && onChange(code)}/>;
}

/** Text for an API error: known codes from the server (e.g. no_permission) are translated. */
export function useErrorText() {
  const {t} = useI18n();
  return (error: string) => { const key = 'err_' + error, text = t(key); return text === key ? error : text; };
}

export function Messages({error, notice}: {error?: string; notice?: string}) {
  const errorText = useErrorText();
  return <>
    {error && <div className="error" role="alert">{errorText(error)}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
  </>;
}

export function Empty({show}: {show: boolean}) {
  const {t} = useI18n();
  return show ? <p className="empty">{t('empty')}</p> : null;
}
