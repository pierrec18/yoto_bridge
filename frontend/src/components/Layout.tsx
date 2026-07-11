import {
  ActionIcon,
  AppShell,
  Button,
  Group,
  NavLink,
  Paper,
  Text,
  Title,
} from "@mantine/core";
import {
  IconCards,
  IconDownload,
  IconLibrary,
  IconLogout,
  IconRadio,
  IconSettings,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { NavLink as RouterNavLink, useLocation } from "react-router-dom";

import { api } from "../api";
import type { AuthStatus } from "../types";

const NAV = [
  { to: "/", label: "Dashboard", icon: IconRadio },
  { to: "/library", label: "Bibliothèque", icon: IconLibrary },
  { to: "/cards", label: "Cartes", icon: IconCards },
  { to: "/settings", label: "Réglages", icon: IconSettings },
];

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    api.authStatus().then(setAuth).catch(() => setAuth(null));
  }, []);

  useEffect(() => {
    const capture = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", capture);
    return () => window.removeEventListener("beforeinstallprompt", capture);
  }, []);

  const install = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: true } }}
      padding="md"
      className="app-shell"
    >
      <AppShell.Header className="app-header">
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <img src="/icons/app-icon.svg" alt="" className="brand-mark" />
            <Title order={4}>Yoto Bridge</Title>
          </Group>
          <Group gap="xs">
            {installPrompt && (
              <Button
                size="xs"
                variant="light"
                leftSection={<IconDownload size={16} />}
                onClick={install}
                className="install-button"
              >
                Installer
              </Button>
            )}
            {auth?.enabled && (
              <>
                <Title order={6} visibleFrom="sm">
                  {auth.user?.name || auth.user?.email}
                </Title>
                <ActionIcon
                  component="a"
                  href="/api/auth/logout"
                  variant="default"
                  aria-label="Déconnexion"
                >
                  <IconLogout size={18} />
                </ActionIcon>
              </>
            )}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            component={RouterNavLink}
            to={item.to}
            label={item.label}
            leftSection={<item.icon size={18} />}
            active={
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to)
            }
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <div className="page-container">{children}</div>
      </AppShell.Main>

      <Paper component="nav" className="mobile-nav" shadow="lg" radius={0}>
        {NAV.map((item) => {
          const active =
            item.to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.to);
          return (
            <RouterNavLink
              key={item.to}
              to={item.to}
              className={`mobile-nav-link${active ? " active" : ""}`}
            >
              <item.icon size={22} stroke={active ? 2.6 : 2} />
              <Text component="span" size="xs" fw={active ? 700 : 500}>
                {item.label}
              </Text>
            </RouterNavLink>
          );
        })}
      </Paper>
    </AppShell>
  );
}
