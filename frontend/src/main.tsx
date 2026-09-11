import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ErrorBoundary, ErrorPage } from "./components/ErrorBoundary";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      {window.location.pathname === "/" || window.location.pathname === "/index.html" ? <App /> : <ErrorPage notFound />}
    </ErrorBoundary>
  </React.StrictMode>,
);
