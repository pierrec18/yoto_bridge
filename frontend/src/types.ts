// Types miroir des schémas Pydantic du backend.

export type PlaybackMode =
  | "fixed"
  | "playlist"
  | "album"
  | "random"
  | "smart"
  | "search";

export interface CardTrack {
  id: number;
  track_number: number;
  mode: PlaybackMode;
  label: string | null;
  config: Record<string, unknown>;
  position: number;
  last_song_id: string | null;
}

export interface Card {
  id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  track_count: number;
  yoto_card_id: string | null;
  created_at: string;
  updated_at: string;
  tracks: CardTrack[];
}

export interface Settings {
  provider: string;
  navidrome_url: string | null;
  username: string | null;
  configured: boolean;
}

export interface ConnectionTestResult {
  ok: boolean;
  detail: string;
}

export interface Track {
  id: string;
  title: string;
  artist: string | null;
  album: string | null;
  genre: string | null;
  year: number | null;
  duration: number | null;
}

export interface Playlist {
  id: string;
  name: string;
  song_count: number | null;
}

export interface Album {
  id: string;
  name: string;
  artist: string | null;
  year: number | null;
}

export interface Artist {
  id: string;
  name: string;
  album_count: number | null;
}

export interface SyncResult {
  tracks: number;
  albums: number;
  playlists: number;
  artists: number;
  genres: number;
}

export interface DashboardStats {
  navidrome_configured: boolean;
  navidrome_online: boolean;
  cards: number;
  tracks: number;
  plays: number;
}

export interface HistoryEntry {
  id: number;
  card_id: number;
  track_number: number;
  song_id: string;
  song_title: string | null;
  artist: string | null;
  album: string | null;
  played_at: string;
}
