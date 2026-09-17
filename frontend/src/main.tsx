import { PolicyPage } from "./components/PolicyPage";
import { syncOfflineStorage } from "./lib/storage";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ErrorBoundary, ErrorPage } from "./components/ErrorBoundary";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      {window.location.pathname === "/" || window.location.pathname === "/index.html" ? <App /> : ["/privacy", "/terms", "/cookies"].includes(window.location.pathname) ? <PolicyPage path={window.location.pathname} /> : <ErrorPage notFound />}
    </ErrorBoundary>
  </React.StrictMode>,
);

void syncOfflineStorage().catch(() => console.warn('Device storage is unavailable. Online use remains available.'));
