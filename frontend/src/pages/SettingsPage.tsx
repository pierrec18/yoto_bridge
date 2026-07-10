import {
  Alert,
  Badge,
  Button,
  Code,
  CopyButton,
  Divider,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconCopy, IconPlugConnected, IconRefresh } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import type { YotoStatus } from "../types";

export function SettingsPage() {
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; detail: string } | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [yoto, setYoto] = useState<YotoStatus | null>(null);
  const [clientId, setClientId] = useState("");

  useEffect(() => {
    api.getSettings().then((s) => {
      setUrl(s.navidrome_url ?? "");
      setUsername(s.username ?? "");
      setToken(s.stream_token);
    });
    api.yotoStatus().then(setYoto).catch(() => setYoto(null));

    const params = new URLSearchParams(window.location.search);
    const yotoParam = params.get("yoto");
    if (yotoParam === "connected") {
      notifications.show({ title: "Yoto connecté", message: "Compte Yoto lié.", color: "green" });
      window.history.replaceState({}, "", window.location.pathname);
    } else if (yotoParam === "error") {
      notifications.show({ title: "Échec Yoto", message: "La connexion a échoué.", color: "red" });
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const saveClientId = async () => {
    setYoto(await api.setYotoConfig(clientId.trim()));
    setClientId("");
    notifications.show({ message: "client_id enregistré", color: "green" });
  };

  const connectYoto = async () => {
    const { authorize_url } = await api.yotoLogin();
    window.location.href = authorize_url;
  };

  const disconnectYoto = async () => {
    setYoto(await api.yotoDisconnect());
  };

  const resetToken = async () => {
    if (
      !window.confirm(
        "Réinitialiser le token invalidera toutes les URLs déjà déposées sur tes cartes Yoto. Continuer ?",
      )
    )
      return;
    setResetting(true);
    try {
      const res = await api.resetStreamToken();
      setToken(res.stream_token);
      notifications.show({
        title: "Token réinitialisé",
        message: "Recopie les URLs de streaming dans tes cartes Yoto.",
        color: "orange",
      });
    } catch (err) {
      notifications.show({ title: "Erreur", message: (err as Error).message, color: "red" });
    } finally {
      setResetting(false);
    }
  };

  const payload = () => ({ navidrome_url: url, username, password });

  const runTest = async () => {
    setTesting(true);
    setTest(null);
    try {
      setTest(await api.testConnection(payload()));
    } catch (err) {
      setTest({ ok: false, detail: (err as Error).message });
    } finally {
      setTesting(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.updateSettings(payload());
      notifications.show({ title: "Enregistré", message: "Configuration Navidrome mise à jour", color: "green" });
    } catch (err) {
      notifications.show({ title: "Erreur", message: (err as Error).message, color: "red" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Title order={2} mb="lg">
        Réglages Navidrome
      </Title>
      <Stack maw={480}>
        <TextInput
          label="URL Navidrome"
          placeholder="https://navidrome.exemple.fr"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
        />
        <TextInput
          label="Utilisateur"
          value={username}
          onChange={(e) => setUsername(e.currentTarget.value)}
        />
        <PasswordInput
          label="Mot de passe"
          description="Laisser vide pour conserver le mot de passe actuel"
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
        />

        {test && (
          <Alert color={test.ok ? "green" : "red"} title={test.ok ? "Connexion réussie" : "Échec"}>
            {test.detail}
          </Alert>
        )}

        <Group>
          <Button
            variant="default"
            leftSection={<IconPlugConnected size={16} />}
            onClick={runTest}
            loading={testing}
          >
            Tester la connexion
          </Button>
          <Button onClick={save} loading={saving}>
            Enregistrer
          </Button>
        </Group>

        <Divider my="md" />

        <Title order={4}>Token de streaming</Title>
        <Text size="sm" c="dimmed">
          Ce jeton est intégré aux URLs <code>/stream</code> déposées sur tes cartes Yoto. En cas
          de fuite, réinitialise-le : les anciennes URLs cesseront de fonctionner et tu devras les
          recopier depuis l'éditeur de carte.
        </Text>
        <Group>
          <TextInput readOnly value={token ?? ""} style={{ flex: 1 }} aria-label="Token" />
          <CopyButton value={token ?? ""}>
            {({ copied, copy }) => (
              <Button
                variant="default"
                leftSection={copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                onClick={copy}
              >
                {copied ? "Copié" : "Copier"}
              </Button>
            )}
          </CopyButton>
          <Button
            color="red"
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={resetToken}
            loading={resetting}
          >
            Réinitialiser
          </Button>
        </Group>

        <Divider my="md" />

        <Group>
          <Title order={4}>Compte Yoto</Title>
          {yoto?.connected ? (
            <Badge color="green">Connecté</Badge>
          ) : (
            <Badge color="gray">Non connecté</Badge>
          )}
        </Group>
        <Text size="sm" c="dimmed">
          Permet de publier automatiquement tes cartes MYO (pistes stream et fichiers hors ligne).
          Renseigne le <code>client_id</code> fourni par Yoto, puis déclare cette URL de redirection
          dans le portail développeur Yoto :
        </Text>
        {yoto && (
          <Group gap="xs">
            <Code>{yoto.redirect_uri}</Code>
            <CopyButton value={yoto.redirect_uri}>
              {({ copied, copy }) => (
                <Button size="xs" variant="subtle" onClick={copy}>
                  {copied ? "Copié" : "Copier"}
                </Button>
              )}
            </CopyButton>
          </Group>
        )}
        <Group align="flex-end">
          <TextInput
            label="client_id Yoto"
            placeholder={yoto?.client_id_set ? "•••••• (défini)" : "client_id"}
            value={clientId}
            onChange={(e) => setClientId(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Button variant="default" onClick={saveClientId} disabled={!clientId.trim()}>
            Enregistrer
          </Button>
        </Group>
        <Group>
          {yoto?.connected ? (
            <Button color="red" variant="light" onClick={disconnectYoto}>
              Déconnecter
            </Button>
          ) : (
            <Button
              leftSection={<IconPlugConnected size={16} />}
              onClick={connectYoto}
              disabled={!yoto?.client_id_set}
            >
              Connecter mon compte Yoto
            </Button>
          )}
        </Group>
      </Stack>
    </>
  );
}
