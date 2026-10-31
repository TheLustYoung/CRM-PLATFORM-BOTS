import {forwardRef, useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent} from 'react';
import {useI18n} from '../services/i18n';

/**
 * WYSIWYG editor for Telegram posts: bold, italic, underline, strikethrough, spoiler, monospace,
 * code block, link and quote, with Telegram Desktop's keyboard shortcuts. The value is Telegram HTML;
 * the server cleans it again with an allow-list before anything is sent.
 */

const escape = (text: string) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const INLINE: Record<string, string> = {B: 'b', STRONG: 'b', I: 'i', EM: 'i', U: 'u', S: 's', STRIKE: 's', DEL: 's', CODE: 'code'};

function serialize(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return escape(node.textContent ?? '');
  if (!(node instanceof HTMLElement)) return '';
  const inner = Array.from(node.childNodes).map(serialize).join('');
  const tag = node.tagName;
  if (tag === 'BR') return '\n';
  if (INLINE[tag]) return inner ? `<${INLINE[tag]}>${inner}</${INLINE[tag]}>` : '';
  if (tag === 'SPAN' && node.classList.contains('tg-spoiler')) return inner ? `<tg-spoiler>${inner}</tg-spoiler>` : '';
  if (tag === 'A') {
    const href = node.getAttribute('href') ?? '';
    return /^(https?:\/\/|tg:\/\/)/i.test(href) ? `<a href="${escape(href).replace(/"/g, '&quot;')}">${inner}</a>` : inner;
  }
  if (tag === 'PRE') return `\n<pre>${escape(node.textContent ?? '')}</pre>\n`;
  if (tag === 'BLOCKQUOTE') return `\n<blockquote>${inner.replace(/^\n+|\n+$/g, '')}</blockquote>\n`;
  if (tag === 'DIV' || tag === 'P') return '\n' + inner;  // a new line typed with Enter
  return inner;
}

/** Editor HTML → Telegram HTML (tidy line breaks). */
export function toTelegram(root: HTMLElement): string {
  return Array.from(root.childNodes).map(serialize).join('').replace(/\n{3,}/g, '\n\n').replace(/^\n+|\n+$/g, '');
}

/** Telegram HTML (from our server, already cleaned) → editor/preview HTML. */
export function fromTelegram(html: string): string {
  return html.replace(/<tg-spoiler>/g, '<span class="tg-spoiler">').replace(/<\/tg-spoiler>/g, '</span>')
    .replace(/<blockquote expandable>/g, '<blockquote>').replace(/\n/g, '<br>');
}

type Tool = {key: string; label: string; icon: string; run: () => void; hotkey: string};
export type PostEditorHandle = {focus: () => void; set: (html: string) => void};

export const PostEditor = forwardRef<PostEditorHandle, {onChange: (html: string, length: number) => void; limit: number; length: number}>(
  function PostEditor({onChange, limit, length}, ref) {
    const {t} = useI18n();
    const box = useRef<HTMLDivElement>(null);
    const saved = useRef<Range | null>(null);
    const [link, setLink] = useState<string | null>(null);
    const [active, setActive] = useState<Set<string>>(new Set());

    const emit = () => { if (box.current) onChange(toTelegram(box.current), (box.current.innerText || '').replace(/\n$/, '').length); };
    useImperativeHandle(ref, () => ({
      focus: () => box.current?.focus(),
      set: (html: string) => { if (box.current) { box.current.innerHTML = fromTelegram(html); emit(); } },
    }));
    useEffect(() => { document.execCommand('styleWithCSS', false, 'false'); }, []);

    const selection = () => {
      const sel = window.getSelection();
      if (!sel || !sel.rangeCount || !box.current?.contains(sel.anchorNode)) return null;
      return sel.getRangeAt(0);
    };
    const closest = (selector: string) => {
      const node = selection()?.commonAncestorContainer;
      const el = node instanceof Element ? node : node?.parentElement;
      const found = el?.closest(selector);
      return found && box.current?.contains(found) ? found as HTMLElement : null;
    };
    const unwrap = (el: HTMLElement) => { el.replaceWith(...Array.from(el.childNodes)); };
    /** Wrap the selection in an element, or remove the wrapper if the selection is already inside one (toggle). */
    const wrap = (tag: string, className?: string) => {
      const selector = className ? `${tag}.${className}` : tag;
      const existing = closest(selector);
      if (existing) { unwrap(existing); emit(); return; }
      const range = selection();
      if (!range || range.collapsed) return;
      const el = document.createElement(tag);
      if (className) el.className = className;
      el.appendChild(range.extractContents());
      range.insertNode(el);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      const after = document.createRange();
      after.selectNodeContents(el);
      sel?.addRange(after);
      emit();
    };
    const command = (name: string) => { document.execCommand(name); emit(); refresh(); };
    const openLink = () => {
      const range = selection();
      if (!range) return;
      saved.current = range.cloneRange();
      setLink((closest('a') as HTMLAnchorElement | null)?.getAttribute('href') ?? 'https://');
    };
    const applyLink = (url: string | null) => {
      const sel = window.getSelection();
      if (saved.current) { sel?.removeAllRanges(); sel?.addRange(saved.current); }
      const current = closest('a');
      if (url === null || !url.trim() || url.trim() === 'https://') { if (current) unwrap(current); }
      else if (current) current.setAttribute('href', url.trim());
      else document.execCommand('createLink', false, url.trim());
      setLink(null); emit(); box.current?.focus();
    };
    const clear = () => {
      const range = selection();
      if (!range || range.collapsed) return;
      const text = range.toString();
      range.deleteContents();
      range.insertNode(document.createTextNode(text));
      emit();
    };
    const refresh = () => {
      const on = new Set<string>();
      for (const [key, selector] of [['bold', 'b,strong'], ['italic', 'i,em'], ['underline', 'u'], ['strike', 's,strike,del'],
        ['spoiler', 'span.tg-spoiler'], ['code', 'code'], ['pre', 'pre'], ['link', 'a'], ['quote', 'blockquote']] as const) {
        if (closest(selector)) on.add(key);
      }
      setActive(on);
    };

    const tools: Tool[] = [
      {key: 'bold', label: t('fmtBold'), icon: 'B', run: () => command('bold'), hotkey: 'Ctrl+B'},
      {key: 'italic', label: t('fmtItalic'), icon: 'I', run: () => command('italic'), hotkey: 'Ctrl+I'},
      {key: 'underline', label: t('fmtUnderline'), icon: 'U', run: () => command('underline'), hotkey: 'Ctrl+U'},
      {key: 'strike', label: t('fmtStrike'), icon: 'S', run: () => command('strikeThrough'), hotkey: 'Ctrl+Shift+X'},
      {key: 'spoiler', label: t('fmtSpoiler'), icon: '▒', run: () => wrap('span', 'tg-spoiler'), hotkey: 'Ctrl+Shift+P'},
      {key: 'code', label: t('fmtCode'), icon: '</>', run: () => wrap('code'), hotkey: 'Ctrl+Shift+M'},
      {key: 'pre', label: t('fmtPre'), icon: '{ }', run: () => wrap('pre'), hotkey: ''},
      {key: 'link', label: t('fmtLink'), icon: '🔗', run: openLink, hotkey: 'Ctrl+K'},
      {key: 'quote', label: t('fmtQuote'), icon: '❝', run: () => wrap('blockquote'), hotkey: 'Ctrl+Shift+.'},
      {key: 'clear', label: t('fmtClear'), icon: 'T̸', run: clear, hotkey: 'Ctrl+Shift+N'},
    ];

    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const key = e.key.toLowerCase();
      const map: Record<string, () => void> = e.shiftKey
        ? {x: tools[3].run, p: tools[4].run, m: tools[5].run, '.': tools[8].run, '>': tools[8].run, n: clear}
        : {k: openLink};  // Ctrl+B / I / U are handled natively by the browser
      if (map[key]) { e.preventDefault(); map[key](); }
    };

    return <div className="post-editor">
      <div className="post-toolbar" role="toolbar" aria-label={t('composeTitle')}>
        {tools.map(tool => <button key={tool.key} type="button" className={'fmt-' + tool.key + (active.has(tool.key) ? ' on' : '')}
          title={tool.hotkey ? `${tool.label} · ${tool.hotkey}` : tool.label} aria-label={tool.label} aria-pressed={active.has(tool.key)}
          onMouseDown={e => e.preventDefault()} onClick={tool.run}>{tool.icon}</button>)}
      </div>
      {link !== null && <form className="link-bar" onSubmit={e => { e.preventDefault(); applyLink(link); }}>
        <input autoFocus type="url" value={link} placeholder="https://…" onChange={e => setLink(e.target.value)} aria-label={t('fmtLink')}/>
        <button className="primary">{t('apply')}</button>
        <button type="button" onClick={() => applyLink(null)}>{t('removeLink')}</button>
        <button type="button" className="ghost" onClick={() => setLink(null)}>✕</button>
      </form>}
      <div ref={box} className="post-input" contentEditable suppressContentEditableWarning role="textbox" aria-multiline="true"
        aria-label={t('postPlaceholder')} data-placeholder={t('postPlaceholder')} dir="auto"
        onInput={emit} onKeyDown={onKey} onKeyUp={refresh} onMouseUp={refresh}
        onPaste={e => { e.preventDefault(); document.execCommand('insertText', false, e.clipboardData.getData('text/plain')); }}/>
      <div className={'post-counter' + (length > limit ? ' over' : '')}>{t('chars').replace('{count}', String(length)).replace('{limit}', String(limit))}</div>
    </div>;
  });
