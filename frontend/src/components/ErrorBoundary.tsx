import { Component, type ReactNode } from 'react';

export function ErrorPage({ notFound = false }: { notFound?: boolean }) {
  return <main className="standard-error">
    <h1>{notFound ? '404 — Page not found' : 'Something went wrong'}</h1>
    <p>{notFound ? 'The page you requested does not exist.' : 'An unexpected error occurred. Please reload the page and try again.'}</p>
    {!notFound && <p><button onClick={() => window.location.reload()}>Reload page</button></p>}
    <a href="/">Go to homepage</a>
  </main>;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? <ErrorPage /> : this.props.children;
  }
}
