import React from "react";
import { createRoot } from "react-dom/client";
import { OverlayWindow } from "./overlay/overlay_window";
import "./styles/global.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <OverlayWindow />
  </React.StrictMode>
);
