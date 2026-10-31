import {createContext, useContext} from 'react';
import type {Page} from '../components/Sidebar';

/** Permission each page needs (null = every signed-in admin). The server checks every call the same way. */
export const PAGE_PERMISSION: Record<Page, string | null> = {
  overview: null, reports: 'bots.view', bots: 'bots.view', users: 'users.view', jobs: 'downloads.view', files: 'downloads.view',
  ads: 'ads.manage', channel: 'ads.manage', monetization: 'money.view', payments: 'money.view', settings: 'settings.manage', guide: 'bots.view',
  team: 'team.manage',
};

export type AccessInfo = {role: string; permissions: string[]};
export const Access = createContext<{role: string; can: (permission: string | null) => boolean}>({role: 'owner', can: () => true});
export const useAccess = () => useContext(Access);
export const makeCan = (permissions: string[]) => {
  const set = new Set(permissions);
  return (permission: string | null) => permission === null || set.has(permission);
};
