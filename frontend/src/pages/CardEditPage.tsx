import {
  ActionIcon,
  Avatar,
  Badge,
  Button,
  Card as MCard,
  CopyButton,
  Divider,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconCopy, IconListNumbers, IconUpload, IconWand } from "@tabler/icons-react";
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
  const [countOpen, { open: openCount, close: closeCount }] = useDisclosure(false);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [genPlaylist, setGenPlaylist] = useState<string | null>(null);
  const [genStrategy, setGenStrategy] = useState<string>("playlist_expand");
  const [streamToken, setStreamToken] = useState<string | null>(null);
  const [trackCount, setTrackCount] = useState<number>(1);
  const mobile = useMediaQuery("(max-width: 47.99em)");

  const load = () => api.getCard(cardId).then((loaded) => {
    setCard(loaded);
    setTrackCount(loaded.track_count);
  });
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

  const resizeCard = async () => {
    if (!card) return;
    if (
      trackCount < card.track_count &&
      !window.confirm(`Les pistes après la piste ${trackCount} seront supprimées. Continuer ?`)
    ) {
      return;
    }
    await api.updateCard(card.id, {
      name: card.name,
      description: card.description,
      image_url: card.image_url,
      track_count: trackCount,
    });
    closeCount();
    await load();
    notifications.show({ message: `${trackCount} pistes disponibles`, color: "green" });
  };

  if (!card) return <Text>Chargement…</Text>;

  const configureTrack = (trackNumber: number) => {
    setActiveTrack(trackNumber);
    openPicker();
  };

  return (
    <>
      <div className="page-header">
        <div>
          <Title order={2}>{card.name}</Title>
          <Text c="dimmed" size="sm">
            {card.track_count} pistes
          </Text>
        </div>
        <Group>
          <Button leftSection={<IconListNumbers size={16} />} variant="default" onClick={openCount}>
            Nombre de pistes
          </Button>
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
      </div>

      <Table.ScrollContainer minWidth={700} visibleFrom="sm">
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
                    <Group gap="sm" wrap="nowrap">
                      <Avatar
                        src={typeof track.config.cover_url === "string" ? track.config.cover_url : null}
                        radius="sm"
                        size={38}
                      />
                      <Text size="sm">{track.label ?? <Text span c="dimmed">—</Text>}</Text>
                    </Group>
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
                      onClick={() => configureTrack(track.track_number)}
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

      <Stack gap="sm" hiddenFrom="sm">
        {card.tracks.map((track) => {
          const tokenSuffix = streamToken ? `?t=${streamToken}` : "";
          const url = `${window.location.origin}/stream/${card.id}/${track.track_number}${tokenSuffix}`;
          return (
            <MCard key={track.track_number} withBorder radius="xl" padding="md" className="track-mobile-card">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                  <div className="track-number">{track.track_number}</div>
                  <div style={{ minWidth: 0 }}>
                    <Badge color={MODE_COLORS[track.mode]} variant="light" mb={4}>
                      {MODE_LABELS[track.mode]}
                    </Badge>
                    <Text fw={700} size="sm" lineClamp={2}>
                      {track.label || "Piste non configurée"}
                    </Text>
                  </div>
                </Group>
                <CopyButton value={url}>
                  {({ copied, copy }) => (
                    <ActionIcon variant="light" size="lg" onClick={copy} aria-label="Copier l’URL">
                      {copied ? <IconCheck size={18} /> : <IconCopy size={18} />}
                    </ActionIcon>
                  )}
                </CopyButton>
              </Group>

              <Group gap="sm" wrap="nowrap" mt="md">
                <Avatar
                  src={typeof track.config.cover_url === "string" ? track.config.cover_url : null}
                  radius="md"
                  size={56}
                />
                <Text size="sm" c="dimmed">
                  {track.mode === "fixed" ? "Morceau fixe" : "Contenu dynamique"}
                </Text>
              </Group>

              <Divider my="md" />
              <SegmentedControl
                fullWidth
                value={track.delivery}
                onChange={(value) => changeDelivery(track, value as Delivery)}
                data={[
                  { label: "Stream", value: "stream" },
                  { label: "Hors ligne", value: "offline", disabled: track.mode !== "fixed" },
                ]}
              />
              <Button fullWidth variant="light" mt="sm" onClick={() => configureTrack(track.track_number)}>
                Configurer la piste
              </Button>
            </MCard>
          );
        })}
      </Stack>

      <ContentPicker opened={pickerOpen} onClose={closePicker} onSelect={applySelection} />

      <Modal opened={countOpen} onClose={closeCount} title="Nombre de pistes" centered>
        <Stack>
          <Text size="sm" c="dimmed">
            Choisis entre 1 et 100 pistes. Réduire ce nombre supprimera les pistes excédentaires.
          </Text>
          <NumberInput
            value={trackCount}
            onChange={(value) => setTrackCount(Number(value) || 1)}
            min={1}
            max={100}
            clampBehavior="strict"
          />
          <Button onClick={resizeCard}>Appliquer</Button>
        </Stack>
      </Modal>

      <Modal opened={genOpen} onClose={closeGen} title="Génération automatique" fullScreen={mobile}>
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
