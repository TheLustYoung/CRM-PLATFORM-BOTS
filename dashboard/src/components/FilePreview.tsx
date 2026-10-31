import {useEffect, type ReactNode} from 'react';
import {useI18n} from '../services/i18n';
import {bytes} from '../services/format';
import type {Row} from '../services/api';

const IMAGE = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const VIDEO = ['video/mp4', 'video/webm', 'video/quicktime'];
const AUDIO = ['audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/x-m4a'];

export const fileSrc = (file: Row) => `/api/admin/files/${encodeURIComponent(file.id)}/content`;

/** The file itself: picture, player, PDF/text frame, or a note that only Download can open it. */
export function MediaView({file, autoPlay = true}: {file: Row; autoPlay?: boolean}) {
  const {t} = useI18n();
  const src = fileSrc(file), mime = String(file.mime || '').split(';')[0].trim().toLowerCase();
  if (IMAGE.includes(mime)) return <img src={src} alt={file.name}/>;
  if (VIDEO.includes(mime)) return <video src={src} controls autoPlay={autoPlay} playsInline/>;
  if (AUDIO.includes(mime)) return <audio src={src} controls autoPlay={autoPlay}/>;
  if (mime === 'application/pdf' || mime === 'text/plain') return <iframe src={src} title={file.name}/>;
  return <div className="no-preview">📄<p>{t('noPreview')}</p></div>;
}

/** Pop-up window shell: closes on ✕, Esc or a click outside. */
export function Modal({title, subtitle, onClose, footer, children}: {title: ReactNode; subtitle?: ReactNode; onClose: () => void; footer?: ReactNode; children: ReactNode}) {
  const {t} = useI18n();
  useEffect(() => {
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);
  return <div className="modal-backdrop" onClick={onClose}>
    <div className="modal" role="dialog" aria-modal="true" onClick={e => e.stopPropagation()}>
      <div className="modal-head">
        <div><strong dir="auto">{title}</strong>{subtitle && <small>{subtitle}</small>}</div>
        <button onClick={onClose} aria-label={t('fileClose')}>✕</button>
      </div>
      {children}
      <div className="modal-foot">{footer}<button onClick={onClose}>{t('fileClose')}</button></div>
    </div>
  </div>;
}

export function DownloadLink({file}: {file: Row}) {
  const {t} = useI18n();
  return <a className="button primary" href={fileSrc(file) + '?download=1'} download={file.name}>⬇ {t('fileDownload')}</a>;
}

/** "View" window: the file shown in place (pictures, video, audio, PDF, text) with a direct Download button. */
export function FilePreview({file, onClose}: {file: Row; onClose: () => void}) {
  return <Modal title={file.name} subtitle={`${bytes(file.size)} · ${file.mime}`} onClose={onClose} footer={<DownloadLink file={file}/>}>
    <div className="modal-body"><MediaView file={file}/></div>
  </Modal>;
}
