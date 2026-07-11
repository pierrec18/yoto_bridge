import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./index.css";

import { createTheme, MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";

const theme = createTheme({
  primaryColor: "yoto",
  primaryShade: 6,
  defaultRadius: "lg",
  fontFamily: '"Avenir Next", "Nunito Sans", ui-rounded, system-ui, sans-serif',
  headings: {
    fontFamily: '"Avenir Next", "Nunito Sans", ui-rounded, system-ui, sans-serif',
    fontWeight: "800",
  },
  colors: {
    yoto: [
      "#fff1e9",
      "#ffdfcf",
      "#ffc0a0",
      "#ff9c6b",
      "#ff7540",
      "#ff5f2b",
      "#f04b18",
      "#ca3a0d",
      "#a62e09",
      "#882505",
    ],
  },
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications position="top-center" />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MantineProvider>
  </React.StrictMode>,
);
