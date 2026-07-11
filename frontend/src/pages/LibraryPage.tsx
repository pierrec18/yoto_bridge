import {
  ActionIcon,
  Avatar,
  Badge,
  Button,
  Card as MCard,
  Group,
  Image,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue, useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconArrowLeft,
  IconDisc,
  IconMicrophone2,
  IconMusic,
  IconPlaylistAdd,
  IconSearch,
  IconUser,
} from "@tabler/icons-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api";
import type { Album, Artist, Card, Track } from "../types";

type LibraryView = "tracks" | "albums" | "artists";

function firstAvailableSlot(card: Card | undefined) {
  if (!card) return null;
  return (
    card.tracks.find((track) => !track.label && Object.keys(track.config).length === 0) ??
    card.tracks[0] ??
    null
  );
}

export function LibraryPage() {
  const mobile = useMediaQuery("(max-width: 47.99em)");
  const [view, setView] = useState<LibraryView>("tracks");
  const [query, setQuery] = useState("");
  const [debounced] = useDebouncedValue(query, 250);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [albumTracks, setAlbumTracks] = useState<Track[]>([]);
  const [artistAlbums, setArtistAlbums] = useState<Album[]>([]);
  const [selectedArtist, setSelectedArtist] = useState<Artist | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);
  const albumRequest = useRef(0);
  const artistRequest = useRef(0);

  const [addTrack, setAddTrack] = useState<Track | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [cardId, setCardId] = useState<string | null>(null);
  const [slotNumber, setSlotNumber] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (selectedArtist || selectedAlbum) return;
    let active = true;
    if (view === "tracks") {
      api.searchLibrary(debounced, 100)
        .then((rows) => active && setTracks(rows))
        .catch(() => active && setTracks([]));
    } else if (view === "albums") {
      api.albums(debounced)
        .then((rows) => active && setAlbums(rows))
        .catch(() => active && setAlbums([]));
    } else {
      api.artists(debounced)
        .then((rows) => active && setArtists(rows))
        .catch(() => active && setArtists([]));
    }
    return () => {
      active = false;
    };
  }, [view, debounced, selectedArtist, selectedAlbum]);

  const changeView = (next: string | null) => {
    if (!next) return;
    setView(next as LibraryView);
    setSelectedArtist(null);
    setSelectedAlbum(null);
    setArtistAlbums([]);
    setAlbumTracks([]);
    artistRequest.current += 1;
    albumRequest.current += 1;
    setQuery("");
  };

  const openAlbum = async (album: Album) => {
    const request = ++albumRequest.current;
    setSelectedAlbum(album);
    setAlbumTracks([]);
    try {
      const rows = await api.albumTracks(album.id);
      if (request === albumRequest.current) setAlbumTracks(rows);
    } catch (error) {
      if (request !== albumRequest.current) return;
      notifications.show({
        title: "Album inaccessible",
        message: (error as Error).message,
        color: "red",
      });
    }
  };

  const openArtist = async (artist: Artist) => {
    const request = ++artistRequest.current;
    setSelectedArtist(artist);
    setArtistAlbums([]);
    try {
      const rows = await api.artistAlbums(artist.id);
      if (request === artistRequest.current) setArtistAlbums(rows);
    } catch (error) {
      if (request !== artistRequest.current) return;
      notifications.show({
        title: "Artiste inaccessible",
        message: (error as Error).message,
        color: "red",
      });
    }
  };

  const goBack = () => {
    if (selectedAlbum) {
      albumRequest.current += 1;
      setSelectedAlbum(null);
      setAlbumTracks([]);
      return;
    }
    artistRequest.current += 1;
    setSelectedArtist(null);
    setArtistAlbums([]);
  };

  const openAdd = async (track: Track) => {
    const availableCards = await api.listCards();
    setCards(availableCards);
    setAddTrack(track);
    const firstCard = availableCards[0];
    setCardId(firstCard ? String(firstCard.id) : null);
    const firstSlot = firstAvailableSlot(firstCard);
    setSlotNumber(firstSlot ? String(firstSlot.track_number) : null);
  };

  const selectedCard = useMemo(
    () => cards.find((card) => String(card.id) === cardId) ?? null,
    [cards, cardId],
  );

  const selectedSlot = selectedCard?.tracks.find(
    (track) => String(track.track_number) === slotNumber,
  );

  const selectCard = (value: string | null) => {
    setCardId(value);
    const card = cards.find((item) => String(item.id) === value);
    const firstSlot = firstAvailableSlot(card);
    setSlotNumber(firstSlot ? String(firstSlot.track_number) : null);
  };

  const addToCard = async () => {
    if (!addTrack || !selectedCard || !selectedSlot) return;
    const configured = Boolean(selectedSlot.label || Object.keys(selectedSlot.config).length);
    if (
      configured &&
      !window.confirm(
        `La piste ${selectedSlot.track_number} contient déjà « ${selectedSlot.label || "un contenu"} ». La remplacer ?`,
      )
    ) {
      return;
    }

    setAdding(true);
    try {
      await api.setTrack(selectedCard.id, selectedSlot.track_number, {
        track_number: selectedSlot.track_number,
        mode: "fixed",
        delivery: "stream",
        label: `${addTrack.title} — ${addTrack.artist ?? ""}`.trim(),
        config: {
          song_id: addTrack.id,
          cover_art: addTrack.cover_art,
          cover_url: addTrack.cover_url,
        },
      });
      notifications.show({
        title: "Morceau ajouté",
        message: `${selectedCard.name} · piste ${selectedSlot.track_number}`,
        color: "green",
      });
      setAddTrack(null);
    } catch (error) {
      notifications.show({ title: "Ajout impossible", message: (error as Error).message, color: "red" });
    } finally {
      setAdding(false);
    }
  };

  const contextTitle = selectedAlbum
    ? selectedAlbum.name
    : selectedArtist
      ? selectedArtist.name
      : "Bibliothèque";

  const visibleTracks = selectedAlbum ? albumTracks : tracks;
  const visibleAlbums = selectedArtist ? artistAlbums : albums;

  const empty =
    selectedAlbum || view === "tracks"
      ? visibleTracks.length === 0
      : selectedArtist || view === "albums"
        ? visibleAlbums.length === 0
        : artists.length === 0;

  return (
    <>
      <div className="page-header">
        <div>
          <Title order={2}>{contextTitle}</Title>
          {(selectedArtist || selectedAlbum) && (
            <Text size="sm" c="dimmed">
              {selectedAlbum?.artist || `${visibleAlbums.length} albums`}
            </Text>
          )}
        </div>
      </div>

      {(selectedArtist || selectedAlbum) && (
        <Button variant="subtle" leftSection={<IconArrowLeft size={17} />} onClick={goBack} mb="md">
          {selectedAlbum && selectedArtist ? selectedArtist.name : "Retour"}
        </Button>
      )}

      {!selectedArtist && !selectedAlbum && (
        <>
          <Tabs value={view} onChange={changeView} mb="md" className="mobile-tabs">
            <Tabs.List>
              <Tabs.Tab value="tracks" leftSection={<IconMusic size={16} />}>Morceaux</Tabs.Tab>
              <Tabs.Tab value="albums" leftSection={<IconDisc size={16} />}>Albums</Tabs.Tab>
              <Tabs.Tab value="artists" leftSection={<IconMicrophone2 size={16} />}>Artistes</Tabs.Tab>
            </Tabs.List>
          </Tabs>
          <TextInput
            placeholder={
              view === "tracks"
                ? "Rechercher un titre, artiste ou album…"
                : view === "albums"
                  ? "Rechercher un album ou un artiste…"
                  : "Rechercher un artiste…"
            }
            leftSection={<IconSearch size={16} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            mb="lg"
            maw={520}
          />
        </>
      )}

      {empty ? (
        <Text c="dimmed">Aucun résultat. Pense à lancer une synchronisation.</Text>
      ) : selectedAlbum || view === "tracks" ? (
        <TrackResults tracks={visibleTracks} onAdd={openAdd} showNumbers={Boolean(selectedAlbum)} />
      ) : selectedArtist || view === "albums" ? (
        <AlbumResults albums={visibleAlbums} onOpen={openAlbum} />
      ) : (
        <ArtistResults artists={artists} onOpen={openArtist} />
      )}

      <Modal
        opened={Boolean(addTrack)}
        onClose={() => setAddTrack(null)}
        title="Ajouter à une carte"
        fullScreen={mobile}
        centered
      >
        <Stack>
          {addTrack && (
            <Group wrap="nowrap">
              <Avatar src={addTrack.cover_url} radius="md" size={58} />
              <div>
                <Text fw={700}>{addTrack.title}</Text>
                <Text size="sm" c="dimmed">{addTrack.artist}</Text>
              </div>
            </Group>
          )}
          {cards.length === 0 ? (
            <Text c="dimmed">Crée d’abord une carte avant d’ajouter ce morceau.</Text>
          ) : (
            <>
              <Select
                label="Carte"
                data={cards.map((card) => ({ value: String(card.id), label: card.name }))}
                value={cardId}
                onChange={selectCard}
              />
              <Select
                label="Emplacement"
                data={(selectedCard?.tracks ?? []).map((track) => ({
                  value: String(track.track_number),
                  label: `Piste ${track.track_number} — ${track.label || "Vide"}`,
                }))}
                value={slotNumber}
                onChange={setSlotNumber}
                searchable
              />
              {selectedSlot && (selectedSlot.label || Object.keys(selectedSlot.config).length > 0) && (
                <Badge color="orange" variant="light" size="lg">
                  Cet emplacement sera remplacé
                </Badge>
              )}
              <Button onClick={addToCard} loading={adding} disabled={!selectedSlot}>
                Ajouter le morceau
              </Button>
            </>
          )}
        </Stack>
      </Modal>
    </>
  );
}

function trackPosition(track: Track) {
  if (!track.track_number) return null;
  return track.disc_number && track.disc_number > 1
    ? `${track.disc_number}.${track.track_number}`
    : String(track.track_number);
}

function TrackResults({
  tracks,
  onAdd,
  showNumbers,
}: {
  tracks: Track[];
  onAdd: (track: Track) => void;
  showNumbers: boolean;
}) {
  return (
    <>
      <Table.ScrollContainer minWidth={720} visibleFrom="sm">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Morceau</Table.Th>
              <Table.Th>Artiste</Table.Th>
              <Table.Th>Album</Table.Th>
              <Table.Th>Année</Table.Th>
              <Table.Th w={70} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {tracks.map((track) => (
              <Table.Tr key={track.id}>
                <Table.Td>
                  <Group gap="sm" wrap="nowrap">
                    <Avatar src={track.cover_url} radius="sm" size={42} />
                    {showNumbers && trackPosition(track) && (
                      <Badge color="gray" variant="light" size="sm">{trackPosition(track)}</Badge>
                    )}
                    <Text size="sm" fw={600}>{track.title}</Text>
                  </Group>
                </Table.Td>
                <Table.Td>{track.artist}</Table.Td>
                <Table.Td>{track.album}</Table.Td>
                <Table.Td>{track.year}</Table.Td>
                <Table.Td>
                  <Tooltip label="Ajouter à une carte">
                    <ActionIcon variant="light" size="lg" onClick={() => onAdd(track)}>
                      <IconPlaylistAdd size={19} />
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Stack gap="sm" hiddenFrom="sm">
        {tracks.map((track) => (
          <MCard key={track.id} withBorder radius="xl" padding="md">
            <Group gap="md" wrap="nowrap" align="flex-start">
              <Avatar src={track.cover_url} radius="md" size={64} />
              <div style={{ minWidth: 0, flex: 1 }}>
                {showNumbers && trackPosition(track) && (
                  <Badge color="gray" variant="light" size="sm" mb={4}>{trackPosition(track)}</Badge>
                )}
                <Text fw={700} lineClamp={2}>{track.title}</Text>
                <Text size="sm" c="dimmed" lineClamp={1}>{track.artist ?? "Artiste inconnu"}</Text>
                <Text size="xs" c="dimmed" mt={4} lineClamp={1}>{track.album ?? "Album inconnu"}</Text>
              </div>
            </Group>
            <Button
              fullWidth
              variant="light"
              mt="md"
              leftSection={<IconPlaylistAdd size={17} />}
              onClick={() => onAdd(track)}
            >
              Ajouter à une carte
            </Button>
          </MCard>
        ))}
      </Stack>
    </>
  );
}

function AlbumResults({ albums, onOpen }: { albums: Album[]; onOpen: (album: Album) => void }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 5 }} spacing={{ base: "sm", sm: "lg" }}>
      {albums.map((album) => (
        <MCard
          key={album.id}
          withBorder
          radius="xl"
          padding="sm"
          onClick={() => onOpen(album)}
          style={{ cursor: "pointer" }}
        >
          <MCard.Section>
            <Image src={album.cover_url} h={{ base: 145, sm: 190 }} fallbackSrc="/icons/app-icon.svg" />
          </MCard.Section>
          <Text fw={700} size="sm" mt="sm" lineClamp={2}>{album.name}</Text>
          <Text size="xs" c="dimmed" lineClamp={1}>{album.artist || "Artiste inconnu"}</Text>
        </MCard>
      ))}
    </SimpleGrid>
  );
}

function ArtistResults({ artists, onOpen }: { artists: Artist[]; onOpen: (artist: Artist) => void }) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
      {artists.map((artist) => (
        <MCard
          key={artist.id}
          withBorder
          radius="xl"
          padding="md"
          onClick={() => onOpen(artist)}
          style={{ cursor: "pointer" }}
        >
          <Group wrap="nowrap">
            <Avatar color="yoto" variant="light" radius="xl" size={52}>
              <IconUser size={25} />
            </Avatar>
            <div>
              <Text fw={700}>{artist.name}</Text>
              <Text size="sm" c="dimmed">{artist.album_count ?? 0} albums</Text>
            </div>
          </Group>
        </MCard>
      ))}
    </SimpleGrid>
  );
}
