import {
  ActionIcon,
  AppShell,
  Burger,
  Group,
  NavLink,
  Title,
  useMantineColorScheme,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconCards,
  IconLibrary,
  IconLogout,
  IconMoon,
  IconRadio,
  IconSettings,
  IconSun,
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

export function Layout({ children }: { children: ReactNode }) {
  const [opened, { toggle, close }] = useDisclosure();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const location = useLocation();
  const [auth, setAuth] = useState<AuthStatus | null>(null);

  useEffect(() => {
    api.authStatus().then(setAuth).catch(() => setAuth(null));
  }, []);

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconRadio size={22} />
            <Title order={4}>Yoto Radio Server</Title>
          </Group>
          <Group gap="xs">
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
            <ActionIcon variant="default" onClick={() => toggleColorScheme()} aria-label="Thème">
              {colorScheme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
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
            onClick={close}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
}
