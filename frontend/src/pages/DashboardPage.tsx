import { Badge, Button, Card, Group, SimpleGrid, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconRefresh } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { DashboardStats } from "../types";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card withBorder padding="lg" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={700} fz={28}>
        {value}
      </Text>
    </Card>
  );
}

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [syncing, setSyncing] = useState(false);

  const load = () => api.dashboard().then(setStats).catch(() => setStats(null));
  useEffect(() => {
    load();
  }, []);

  const runSync = async () => {
    setSyncing(true);
    try {
      const result = await api.sync();
      notifications.show({
        title: "Synchronisation terminée",
        message: `${result.tracks} morceaux, ${result.albums} albums, ${result.playlists} playlists`,
        color: "green",
      });
      load();
    } catch (err) {
      notifications.show({
        title: "Échec de la synchronisation",
        message: (err as Error).message,
        color: "red",
      });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <Group justify="space-between" mb="lg">
        <Title order={2}>Dashboard</Title>
        <Button leftSection={<IconRefresh size={16} />} onClick={runSync} loading={syncing}>
          Synchroniser
        </Button>
      </Group>

      <Group mb="lg">
        <Text>État Navidrome :</Text>
        {stats?.navidrome_online ? (
          <Badge color="green">En ligne</Badge>
        ) : stats?.navidrome_configured ? (
          <Badge color="red">Hors ligne</Badge>
        ) : (
          <Badge color="gray">Non configuré</Badge>
        )}
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <StatCard label="Cartes" value={stats?.cards ?? "—"} />
        <StatCard label="Morceaux en cache" value={stats?.tracks ?? "—"} />
        <StatCard label="Lectures" value={stats?.plays ?? "—"} />
      </SimpleGrid>
    </>
  );
}
