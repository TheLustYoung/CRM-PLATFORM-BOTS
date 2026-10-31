import React from 'react';
import {createRoot} from 'react-dom/client';
import {App} from './App';
import '@fontsource/geist-sans/400.css';
import '@fontsource/geist-sans/500.css';
import '@fontsource/geist-sans/600.css';
import '@fontsource/geist-mono/400.css';
// Geist has no Cyrillic: Inter covers Russian glyphs only.
import '@fontsource/inter/cyrillic-400.css';
import '@fontsource/inter/cyrillic-500.css';
import '@fontsource/inter/cyrillic-600.css';
import './styles/main.scss';

// Apply the saved theme before the first paint (no flash of the wrong theme). Dark is the default.
try { document.documentElement.dataset.theme = localStorage.getItem('theme') === 'light' ? 'light' : 'dark'; } catch {}

// The app is installable on phones and tablets only: desktop browsers get no manifest, so no "Install app" offer.
if (matchMedia('(pointer: coarse)').matches && !matchMedia('(any-pointer: fine)').matches) {
  const link = document.createElement('link');
  link.rel = 'manifest';
  link.href = '/manifest.webmanifest';
  document.head.appendChild(link);
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
