import { Alert, Button, Group, PasswordInput, Stack, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlugConnected } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { api } from "../api";

export function SettingsPage() {
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [test, setTest] = useState<{ ok: boolean; detail: string } | null>(null);

  useEffect(() => {
    api.getSettings().then((s) => {
      setUrl(s.navidrome_url ?? "");
      setUsername(s.username ?? "");
    });
  }, []);

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
      </Stack>
    </>
  );
}
