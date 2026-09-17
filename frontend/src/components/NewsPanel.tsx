import { useEffect, useState } from 'react';
import { loadNews } from '../lib/api';
import type { NewsFeed } from '../types';

export function NewsPanel() {
  const [news, setNews] = useState<NewsFeed | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const refresh = () => {
      loadNews(controller.signal).then(data => { setNews(data); setError(''); }).catch(error => {
        if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'News unavailable');
      });
    };
    refresh();
    const timer = setInterval(refresh, 3600000);
    window.addEventListener('online', refresh);
    window.addEventListener('offline', refresh);
    return () => { controller.abort(); clearInterval(timer); window.removeEventListener('online', refresh); window.removeEventListener('offline', refresh); };
  }, [retry]);
  return <section className="news-panel" aria-label="Fantasy football news">
    <h2>Fantasy football & NFL news</h2>
    <p>Daily headlines from RotoWire and ESPN. Article links require internet access.</p>
    <p role="status">{news?.fetched_at ? `${news.stale ? 'Saved news' : 'Last collected'}: ${new Date(news.fetched_at).toLocaleString()}` : error ? 'News unavailable' : news ? 'No news saved yet. Connect to collect headlines.' : 'Loading news…'}</p>
    {error && <p role="alert">{error}</p>}
    {news?.warnings.map(warning => <p key={warning} className="coverage-warning">{warning}</p>)}
    <button onClick={() => setRetry(value => value + 1)}>Check news</button>
    <ul>{news?.articles.slice(0, 30).map(article => <li key={article.url}>
      <a href={article.url} target="_blank" rel="noopener noreferrer">{article.title}</a>
      <small>{article.source} · {new Date(article.published_at).toLocaleString()}</small>
    </li>)}</ul>
  </section>;
}
