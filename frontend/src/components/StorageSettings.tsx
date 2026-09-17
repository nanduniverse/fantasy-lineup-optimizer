import { useState } from 'react';
import { offlineEnabled, setOfflineEnabled } from '../lib/storage';

export function StorageSettings() {
  const [enabled, setEnabled] = useState(offlineEnabled);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function change(value: boolean) {
    setBusy(true); setMessage(''); setEnabled(value);
    try {
      await setOfflineEnabled(value);
      setEnabled(value);
      // Re-load public data for saving, or discard in-memory league credentials after clearing.
      window.location.reload();
    } catch {
      setEnabled(offlineEnabled());
      setMessage('The storage change could not finish. Check your browser’s site-storage settings.');
      setBusy(false);
    }
  }
  return <aside className="storage-settings" aria-label="Device storage settings">
    <label><input type="checkbox" checked={enabled} disabled={busy} onChange={e => void change(e.target.checked)} /> Save on this device for offline use</label>
    <p>Optional: saves the app, players, headlines and matchup selections. Turning it off clears saved data and reloads the page. No tracking. <a href="/cookies">Storage details</a></p>
    {enabled && <button onClick={() => void change(false)} disabled={busy}>Clear saved data and turn off offline saving</button>}
    <span role="status">{busy ? 'Updating storage settings…' : message}</span>
  </aside>;
}
