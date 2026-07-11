import { Avatar, Card, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconSearch } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Track } from "../types";

export function LibraryPage() {
  const [query, setQuery] = useState("");
  const [debounced] = useDebouncedValue(query, 250);
  const [tracks, setTracks] = useState<Track[]>([]);

  useEffect(() => {
    api.searchLibrary(debounced).then(setTracks).catch(() => setTracks([]));
  }, [debounced]);

  return (
    <>
      <div className="page-header">
        <Title order={2}>Bibliothèque</Title>
      </div>
      <TextInput
        placeholder="Recherche instantanée (titre, artiste, album)…"
        leftSection={<IconSearch size={16} />}
        value={query}
        onChange={(e) => setQuery(e.currentTarget.value)}
        mb="md"
        maw={480}
      />

      {tracks.length === 0 ? (
        <Text c="dimmed">Aucun résultat. Pense à lancer une synchronisation.</Text>
      ) : (
        <>
        <Table.ScrollContainer minWidth={600} visibleFrom="sm">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Morceau</Table.Th>
                <Table.Th>Artiste</Table.Th>
                <Table.Th>Album</Table.Th>
                <Table.Th>Genre</Table.Th>
                <Table.Th>Année</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tracks.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>
                    <Group gap="sm" wrap="nowrap">
                      <Avatar src={t.cover_url} radius="sm" size={42} />
                      <Text size="sm" fw={500}>{t.title}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>{t.artist}</Table.Td>
                  <Table.Td>{t.album}</Table.Td>
                  <Table.Td>{t.genre}</Table.Td>
                  <Table.Td>{t.year}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
        <Stack gap="sm" hiddenFrom="sm">
          {tracks.map((track) => (
            <Card key={track.id} withBorder radius="xl" padding="md">
              <Group gap="md" wrap="nowrap" align="flex-start">
                <Avatar src={track.cover_url} radius="md" size={64} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <Text fw={700} lineClamp={2}>{track.title}</Text>
                  <Text size="sm" c="dimmed" lineClamp={1}>{track.artist ?? "Artiste inconnu"}</Text>
                  <Text size="xs" c="dimmed" mt={4} lineClamp={1}>
                    {track.album ?? "Album inconnu"}
                    {track.year ? ` · ${track.year}` : ""}
                  </Text>
                </div>
              </Group>
            </Card>
          ))}
        </Stack>
        </>
      )}
    </>
  );
}
