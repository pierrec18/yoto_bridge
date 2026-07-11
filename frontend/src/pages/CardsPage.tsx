import {
  ActionIcon,
  Button,
  Card as MCard,
  Group,
  Modal,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconCopy, IconPlus, IconTrash } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import type { Card } from "../types";

export function CardsPage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState("");
  const [trackCount, setTrackCount] = useState<number>(20);
  const navigate = useNavigate();
  const mobile = useMediaQuery("(max-width: 47.99em)");

  const load = () => api.listCards().then(setCards).catch(() => setCards([]));
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    const card = await api.createCard({ name, track_count: trackCount });
    close();
    setName("");
    navigate(`/cards/${card.id}`);
  };

  const remove = async (id: number) => {
    await api.deleteCard(id);
    notifications.show({ message: "Carte supprimée", color: "gray" });
    load();
  };

  const duplicate = async (id: number) => {
    await api.duplicateCard(id);
    load();
  };

  return (
    <>
      <div className="page-header">
        <Title order={2}>Cartes</Title>
        <Button className="mobile-full" leftSection={<IconPlus size={16} />} onClick={open}>
          Nouvelle carte
        </Button>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {cards.map((card) => (
          <MCard key={card.id} withBorder padding="lg" radius="xl">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>{card.name}</Text>
              <Group gap={4}>
                <ActionIcon variant="subtle" onClick={() => duplicate(card.id)} aria-label="Dupliquer">
                  <IconCopy size={16} />
                </ActionIcon>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  onClick={() => remove(card.id)}
                  aria-label="Supprimer"
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              {card.track_count} pistes
            </Text>
            <Button variant="light" fullWidth onClick={() => navigate(`/cards/${card.id}`)}>
              Éditer
            </Button>
          </MCard>
        ))}
      </SimpleGrid>

      {cards.length === 0 && <Text c="dimmed">Aucune carte pour l'instant.</Text>}

      <Modal opened={opened} onClose={close} title="Nouvelle carte" fullScreen={mobile}>
        <Stack>
          <TextInput
            label="Nom"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            data-autofocus
          />
          <NumberInput
            label="Nombre de pistes"
            value={trackCount}
            onChange={(v) => setTrackCount(Number(v) || 0)}
            min={1}
            max={500}
          />
          <Button onClick={create}>Créer</Button>
        </Stack>
      </Modal>
    </>
  );
}
