// Only public catalogs, headlines and explicit matchup fields belong here.
export function readSaved<T>(key: string): T | null {
  try { return JSON.parse(localStorage.getItem(`fantasy:v1:${key}`) ?? 'null') as T | null; }
  catch { return null; }
}
export function save<T>(key: string, value: T) {
  try { localStorage.setItem(`fantasy:v1:${key}`, JSON.stringify(value)); }
  catch { /* Storage may be disabled or full; online use still works. */ }
}
