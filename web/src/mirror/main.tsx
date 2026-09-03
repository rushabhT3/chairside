import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../tokens.css";
import "./mirror.css";
import { App } from "./App";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Mirror needs a #root element");

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("../sw.js", { scope: "../" }).catch(() => undefined);
  });
}
