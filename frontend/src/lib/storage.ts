const PREFIX = 'fantasy:v1:';
const CHOICE = 'fantasy:storage-choice';
const SIX_MONTHS = 180 * 86400000;
const THIRTY_DAYS = 30 * 86400000;

export function offlineEnabled(): boolean {
  try {
    const choice = JSON.parse(localStorage.getItem(CHOICE) ?? 'null');
    if (choice && Date.now() - choice.at >= SIX_MONTHS) { localStorage.removeItem(CHOICE); return false; }
    return choice?.enabled === true;
  } catch { return false; }
}

// Never persist league credentials, league names, or contact details.
export function readSaved<T>(key: string): T | null {
  if (!offlineEnabled()) return null;
  try {
    const saved = JSON.parse(localStorage.getItem(`${PREFIX}${key}`) ?? 'null');
    if (!saved || typeof saved.at !== 'number' || Date.now() - saved.at > THIRTY_DAYS) {
      localStorage.removeItem(`${PREFIX}${key}`);
      return null;
    }
    return saved.value as T;
  } catch { return null; }
}
export function save<T>(key: string, value: T) {
  if (!offlineEnabled()) return;
  try { localStorage.setItem(`${PREFIX}${key}`, JSON.stringify({ at: Date.now(), value })); }
  catch { /* Storage may be disabled or full; online use still works. */ }
}

export async function clearSavedData() {
  for (const key of Object.keys(localStorage)) if (key.startsWith(PREFIX)) localStorage.removeItem(key);
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.filter(r => [r.active, r.waiting, r.installing].some(w => w?.scriptURL === `${location.origin}/sw.js`)).map(r => r.unregister()));
  }
  if ('caches' in window) {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith('fantasy-shell-')).map(key => caches.delete(key)));
  }
}

let storageWork = Promise.resolve();
export function syncOfflineStorage() {
  storageWork = storageWork.catch(() => {}).then(async () => {
    if (!offlineEnabled()) { await clearSavedData(); return; }
    if (import.meta.env.PROD && 'serviceWorker' in navigator) {
      await navigator.serviceWorker.register('/sw.js');
    }
  });
  return storageWork;
}

export async function setOfflineEnabled(enabled: boolean) {
  // Recording this choice is necessary to remember the user's storage preference.
  localStorage.setItem(CHOICE, JSON.stringify({ enabled, at: Date.now() }));
  window.dispatchEvent(new Event('fantasy-storage-change'));
  await syncOfflineStorage();
}
