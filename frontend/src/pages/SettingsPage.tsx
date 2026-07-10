import {
  Alert,
  Button,
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

export function SettingsPage() {
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; detail: string } | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    api.getSettings().then((s) => {
      setUrl(s.navidrome_url ?? "");
      setUsername(s.username ?? "");
      setToken(s.stream_token);
    });
  }, []);

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
      </Stack>
    </>
  );
}
