import {
  Button,
  Modal,
  NumberInput,
  ScrollArea,
  SegmentedControl,
  Stack,
  Tabs,
  Text,
  TextInput,
  UnstyledButton,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Album, PlaybackMode, Playlist, Track } from "../types";

export interface TrackSelection {
  mode: PlaybackMode;
  config: Record<string, unknown>;
  label: string;
}

interface Props {
  opened: boolean;
  onClose: () => void;
  onSelect: (selection: TrackSelection) => void;
}

function PickList<T extends { id: string }>({
  items,
  render,
  onPick,
}: {
  items: T[];
  render: (item: T) => string;
  onPick: (item: T) => void;
}) {
  return (
    <ScrollArea h={280}>
      <Stack gap={2}>
        {items.map((item) => (
          <UnstyledButton
            key={item.id}
            onClick={() => onPick(item)}
            p="xs"
            style={{ borderRadius: 6 }}
            className="picker-row"
          >
            <Text size="sm">{render(item)}</Text>
          </UnstyledButton>
        ))}
        {items.length === 0 && <Text c="dimmed" size="sm" p="xs">Aucun résultat.</Text>}
      </Stack>
    </ScrollArea>
  );
}

export function ContentPicker({ opened, onClose, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [debounced] = useDebouncedValue(query, 250);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);

  // Mode recherche dynamique
  const [searchQuery, setSearchQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [minRating, setMinRating] = useState<number | undefined>();
  // Mode aléatoire / smart
  const [dynamicMode, setDynamicMode] = useState<PlaybackMode>("random");

  useEffect(() => {
    if (!opened) return;
    api.searchLibrary(debounced).then(setTracks).catch(() => setTracks([]));
    api.albums(debounced).then(setAlbums).catch(() => setAlbums([]));
  }, [opened, debounced]);

  useEffect(() => {
    if (opened) api.playlists().then(setPlaylists).catch(() => setPlaylists([]));
  }, [opened]);

  const pick = (selection: TrackSelection) => {
    onSelect(selection);
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Configurer la piste" size="lg">
      <Tabs defaultValue="track">
        <Tabs.List mb="sm">
          <Tabs.Tab value="track">Morceau</Tabs.Tab>
          <Tabs.Tab value="album">Album</Tabs.Tab>
          <Tabs.Tab value="playlist">Playlist</Tabs.Tab>
          <Tabs.Tab value="search">Recherche</Tabs.Tab>
          <Tabs.Tab value="dynamic">Aléatoire</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="track">
          <TextInput
            placeholder="Rechercher un morceau…"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            mb="xs"
          />
          <PickList
            items={tracks}
            render={(t) => `${t.title} — ${t.artist ?? "?"}`}
            onPick={(t) =>
              pick({
                mode: "fixed",
                config: { song_id: t.id },
                label: `${t.title} — ${t.artist ?? ""}`.trim(),
              })
            }
          />
        </Tabs.Panel>

        <Tabs.Panel value="album">
          <TextInput
            placeholder="Rechercher un album…"
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            mb="xs"
          />
          <PickList
            items={albums}
            render={(a) => `${a.name} — ${a.artist ?? "?"}`}
            onPick={(a) => pick({ mode: "album", config: { album_id: a.id }, label: a.name })}
          />
        </Tabs.Panel>

        <Tabs.Panel value="playlist">
          <PickList
            items={playlists}
            render={(p) => `${p.name} (${p.song_count ?? 0})`}
            onPick={(p) =>
              pick({ mode: "playlist", config: { playlist_id: p.id }, label: p.name })
            }
          />
        </Tabs.Panel>

        <Tabs.Panel value="search">
          <Stack>
            <TextInput
              label="Texte"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
            />
            <TextInput label="Genre" value={genre} onChange={(e) => setGenre(e.currentTarget.value)} />
            <NumberInput
              label="Note minimale (1-5)"
              min={1}
              max={5}
              value={minRating}
              onChange={(v) => setMinRating(v === "" ? undefined : Number(v))}
            />
            <Button
              onClick={() =>
                pick({
                  mode: "search",
                  config: {
                    query: searchQuery || undefined,
                    genre: genre || undefined,
                    min_rating: minRating,
                  },
                  label: `Recherche : ${searchQuery || genre || "filtres"}`,
                })
              }
            >
              Utiliser cette recherche
            </Button>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="dynamic">
          <Stack>
            <Text size="sm" c="dimmed">
              La piste tire un morceau à chaque lecture depuis toute la bibliothèque.
            </Text>
            <SegmentedControl
              value={dynamicMode}
              onChange={(v) => setDynamicMode(v as PlaybackMode)}
              data={[
                { label: "Aléatoire", value: "random" },
                { label: "Smart", value: "smart" },
              ]}
            />
            <Button
              onClick={() =>
                pick({
                  mode: dynamicMode,
                  config: {},
                  label: dynamicMode === "smart" ? "Smart" : "Aléatoire",
                })
              }
            >
              Appliquer
            </Button>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Modal>
  );
}
