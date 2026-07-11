import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./index.css";

import { createTheme, MantineProvider } from "@mantine/core";
import type { MantineColorScheme } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import type { ReactNode } from "react";
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

// Une ancienne version proposait un toggle et pouvait mémoriser light/dark.
// Sans préférence persistée, Mantine suit `prefers-color-scheme` du système.
localStorage.removeItem("mantine-color-scheme-value");

function systemColorScheme(): Exclude<MantineColorScheme, "auto"> {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function SystemThemeProvider({ children }: { children: ReactNode }) {
  const [colorScheme, setColorScheme] = useState(systemColorScheme);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => setColorScheme(media.matches ? "dark" : "light");
    const syncWhenVisible = () => {
      if (document.visibilityState === "visible") sync();
    };

    // addListener couvre les versions de Safari/iOS qui ne réveillent pas
    // correctement une PWA avec addEventListener lorsque le thème change.
    media.addEventListener?.("change", sync);
    media.addListener?.(sync);
    window.addEventListener("focus", sync);
    document.addEventListener("visibilitychange", syncWhenVisible);
    sync();

    return () => {
      media.removeEventListener?.("change", sync);
      media.removeListener?.(sync);
      window.removeEventListener("focus", sync);
      document.removeEventListener("visibilitychange", syncWhenVisible);
    };
  }, []);

  return (
    <MantineProvider theme={theme} forceColorScheme={colorScheme}>
      {children}
    </MantineProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SystemThemeProvider>
      <Notifications position="top-center" />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </SystemThemeProvider>
  </React.StrictMode>,
);
