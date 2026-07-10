import {
  ActionIcon,
  Badge,
  Button,
  CopyButton,
  Group,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconCopy, IconUpload, IconWand } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../api";
import { ContentPicker, type TrackSelection } from "../components/ContentPicker";
import type { Card, CardTrack, Delivery, PlaybackMode, Playlist } from "../types";

const MODE_LABELS: Record<PlaybackMode, string> = {
  fixed: "Fixe",
  playlist: "Playlist",
  album: "Album",
  random: "Aléatoire",
  smart: "Smart",
  search: "Recherche",
};

const MODE_COLORS: Record<PlaybackMode, string> = {
  fixed: "blue",
  playlist: "grape",
  album: "teal",
  random: "orange",
  smart: "pink",
  search: "cyan",
};

export function CardEditPage() {
  const { id } = useParams();
  const cardId = Number(id);
  const [card, setCard] = useState<Card | null>(null);
  const [activeTrack, setActiveTrack] = useState<number | null>(null);
  const [pickerOpen, { open: openPicker, close: closePicker }] = useDisclosure(false);
  const [genOpen, { open: openGen, close: closeGen }] = useDisclosure(false);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [genPlaylist, setGenPlaylist] = useState<string | null>(null);
  const [genStrategy, setGenStrategy] = useState<string>("playlist_expand");
  const [streamToken, setStreamToken] = useState<string | null>(null);

  const load = () => api.getCard(cardId).then(setCard);
  useEffect(() => {
    load();
    api.playlists().then(setPlaylists).catch(() => setPlaylists([]));
    api.getSettings().then((s) => setStreamToken(s.stream_token)).catch(() => setStreamToken(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cardId]);

  const [publishing, setPublishing] = useState(false);

  const applySelection = async (selection: TrackSelection) => {
    if (activeTrack === null) return;
    const current = card?.tracks.find((t) => t.track_number === activeTrack);
    // Le hors ligne exige un morceau fixe : on retombe sur stream sinon.
    const delivery: Delivery =
      current?.delivery === "offline" && selection.mode === "fixed" ? "offline" : "stream";
    await api.setTrack(cardId, activeTrack, {
      track_number: activeTrack,
      mode: selection.mode,
      delivery,
      label: selection.label,
      config: selection.config,
    });
    await load();
  };

  const changeDelivery = async (track: CardTrack, delivery: Delivery) => {
    await api.setTrack(cardId, track.track_number, {
      track_number: track.track_number,
      mode: track.mode,
      delivery,
      label: track.label,
      config: track.config,
    });
    await load();
  };

  const publish = async () => {
    setPublishing(true);
    try {
      const res = await api.publishCard(cardId);
      notifications.show({
        title: "Carte publiée sur Yoto",
        message: `${res.chapters} pistes · cardId ${res.yoto_card_id ?? "?"}`,
        color: "green",
      });
    } catch (err) {
      notifications.show({ title: "Publication échouée", message: (err as Error).message, color: "red" });
    } finally {
      setPublishing(false);
    }
  };

  const runGenerate = async () => {
    try {
      await api.generate(cardId, {
        strategy: genStrategy,
        source_id: genPlaylist ?? undefined,
      });
      closeGen();
      notifications.show({ message: "Pistes générées", color: "green" });
      load();
    } catch (err) {
      notifications.show({ title: "Erreur", message: (err as Error).message, color: "red" });
    }
  };

  if (!card) return <Text>Chargement…</Text>;

  return (
    <>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>{card.name}</Title>
          <Text c="dimmed" size="sm">
            {card.track_count} pistes
          </Text>
        </div>
        <Group>
          <Button leftSection={<IconWand size={16} />} variant="light" onClick={openGen}>
            Générer automatiquement
          </Button>
          <Button
            leftSection={<IconUpload size={16} />}
            onClick={publish}
            loading={publishing}
          >
            Publier sur Yoto
          </Button>
        </Group>
      </Group>

      <Table.ScrollContainer minWidth={700}>
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={60}>Piste</Table.Th>
              <Table.Th w={110}>Mode</Table.Th>
              <Table.Th>Source</Table.Th>
              <Table.Th w={190}>Livraison</Table.Th>
              <Table.Th w={90}>URL</Table.Th>
              <Table.Th w={110} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {card.tracks.map((track) => {
              const tokenSuffix = streamToken ? `?t=${streamToken}` : "";
              const url = `${window.location.origin}/stream/${card.id}/${track.track_number}${tokenSuffix}`;
              return (
                <Table.Tr key={track.track_number}>
                  <Table.Td>{track.track_number}</Table.Td>
                  <Table.Td>
                    <Badge color={MODE_COLORS[track.mode]} variant="light">
                      {MODE_LABELS[track.mode]}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{track.label ?? <Text span c="dimmed">—</Text>}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Tooltip
                      label="Le mode hors ligne exige un morceau fixe"
                      disabled={track.mode === "fixed"}
                      withArrow
                    >
                      <SegmentedControl
                        size="xs"
                        value={track.delivery}
                        onChange={(v) => changeDelivery(track, v as Delivery)}
                        data={[
                          { label: "Stream", value: "stream" },
                          { label: "Hors ligne", value: "offline", disabled: track.mode !== "fixed" },
                        ]}
                      />
                    </Tooltip>
                  </Table.Td>
                  <Table.Td>
                    <CopyButton value={url}>
                      {({ copied, copy }) => (
                        <Tooltip label={copied ? "Copié" : url} withArrow>
                          <ActionIcon variant="subtle" onClick={copy} aria-label="Copier l'URL">
                            {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </CopyButton>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      size="xs"
                      variant="default"
                      onClick={() => {
                        setActiveTrack(track.track_number);
                        openPicker();
                      }}
                    >
                      Configurer
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <ContentPicker opened={pickerOpen} onClose={closePicker} onSelect={applySelection} />

      <Modal opened={genOpen} onClose={closeGen} title="Génération automatique">
        <Stack>
          <Select
            label="Stratégie"
            data={[
              { value: "playlist_expand", label: "Éclater une playlist (1 piste = 1 morceau fixe)" },
              { value: "playlist", label: "Playlist dynamique (chaque piste avance)" },
              { value: "all_random", label: "Tout en aléatoire" },
            ]}
            value={genStrategy}
            onChange={(v) => setGenStrategy(v ?? "playlist_expand")}
          />
          {genStrategy !== "all_random" && (
            <Select
              label="Playlist source"
              placeholder="Choisir…"
              searchable
              data={playlists.map((p) => ({ value: p.id, label: p.name }))}
              value={genPlaylist}
              onChange={setGenPlaylist}
            />
          )}
          <Button onClick={runGenerate}>Générer</Button>
        </Stack>
      </Modal>
    </>
  );
}
