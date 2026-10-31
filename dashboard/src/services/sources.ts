/** Media sources the bots accept (backend/services/platforms.py) and the bots of the platform. */
export const SOURCES = ['wikimedia', 'archive', 'direct'];
export const SOURCE_TITLES: Record<string, string> = {wikimedia: 'Wikimedia Commons', archive: 'Internet Archive', direct: 'Direct file link', telegram: 'Telegram upload'};
export const sourceTitle = (key: string | null | undefined) => (key && SOURCE_TITLES[key]) || key || '—';
export const BOT_KINDS = ['video', 'media', 'files'];
export const BOT_ICONS: Record<string, string> = {video: 'play', media: 'image', files: 'folder'};
