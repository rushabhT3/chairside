import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../tokens.css";
import "./floor.css";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("Floor needs a #root element");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
