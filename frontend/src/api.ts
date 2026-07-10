// Client API typé. Toute la logique métier reste côté serveur : ce module
// ne fait qu'appeler les endpoints REST.

import type {
  Album,
  Artist,
  Card,
  CardTrack,
  ConnectionTestResult,
  DashboardStats,
  HistoryEntry,
  PlaybackMode,
  Playlist,
  Settings,
  SyncResult,
  Track,
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* corps non JSON */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface CardTrackInput {
  track_number: number;
  mode: PlaybackMode;
  label?: string | null;
  config: Record<string, unknown>;
}

export const api = {
  // Settings
  getSettings: () => request<Settings>("/api/settings"),
  updateSettings: (data: { navidrome_url: string; username: string; password: string }) =>
    request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(data) }),
  testConnection: (data: { navidrome_url: string; username: string; password: string }) =>
    request<ConnectionTestResult>("/api/settings/test", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  resetStreamToken: () =>
    request<{ stream_token: string }>("/api/settings/reset-token", { method: "POST" }),

  // Sync + stats
  sync: () => request<SyncResult>("/api/sync", { method: "POST" }),
  dashboard: () => request<DashboardStats>("/api/stats/dashboard"),

  // Library
  searchLibrary: (q: string, limit = 50) =>
    request<Track[]>(`/api/library/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  playlists: () => request<Playlist[]>("/api/library/playlists"),
  albums: (q = "") => request<Album[]>(`/api/library/albums?q=${encodeURIComponent(q)}`),
  artists: () => request<Artist[]>("/api/library/artists"),

  // Cards
  listCards: () => request<Card[]>("/api/cards"),
  getCard: (id: number) => request<Card>(`/api/cards/${id}`),
  createCard: (data: { name: string; description?: string; track_count: number }) =>
    request<Card>("/api/cards", { method: "POST", body: JSON.stringify(data) }),
  updateCard: (
    id: number,
    data: { name: string; description?: string | null; image_url?: string | null; track_count: number },
  ) => request<Card>(`/api/cards/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteCard: (id: number) => request<void>(`/api/cards/${id}`, { method: "DELETE" }),
  duplicateCard: (id: number) =>
    request<Card>(`/api/cards/${id}/duplicate`, { method: "POST" }),
  setTrack: (cardId: number, trackNumber: number, data: CardTrackInput) =>
    request<CardTrack>(`/api/cards/${cardId}/tracks/${trackNumber}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  generate: (cardId: number, data: { strategy: string; source_id?: string }) =>
    request<Card>(`/api/cards/${cardId}/generate`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cardHistory: (id: number) => request<HistoryEntry[]>(`/api/cards/${id}/history`),
};
