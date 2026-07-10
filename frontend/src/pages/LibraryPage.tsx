import { Table, Text, TextInput, Title } from "@mantine/core";
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
      <Title order={2} mb="lg">
        Bibliothèque
      </Title>
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
        <Table.ScrollContainer minWidth={600}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Titre</Table.Th>
                <Table.Th>Artiste</Table.Th>
                <Table.Th>Album</Table.Th>
                <Table.Th>Genre</Table.Th>
                <Table.Th>Année</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tracks.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>{t.title}</Table.Td>
                  <Table.Td>{t.artist}</Table.Td>
                  <Table.Td>{t.album}</Table.Td>
                  <Table.Td>{t.genre}</Table.Td>
                  <Table.Td>{t.year}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </>
  );
}
