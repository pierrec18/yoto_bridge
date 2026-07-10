import { Route, Routes } from "react-router-dom";
import { Center, Loader } from "@mantine/core";
import { useEffect, useState } from "react";

import { api } from "./api";
import { Layout } from "./components/Layout";
import { CardEditPage } from "./pages/CardEditPage";
import { CardsPage } from "./pages/CardsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LibraryPage } from "./pages/LibraryPage";
import { SettingsPage } from "./pages/SettingsPage";

function AuthenticatedApp() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/cards/:id" element={<CardEditPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api.authStatus()
      .then((status) => {
        if (!status.authenticated) {
          const next = `${window.location.pathname}${window.location.search}`;
          window.location.assign(`/api/auth/login?next=${encodeURIComponent(next)}`);
          return;
        }
        setReady(true);
      })
      .catch(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }
  return <AuthenticatedApp />;
}
