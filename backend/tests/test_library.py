"""Tests de navigation hiérarchique dans la bibliothèque en cache."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LibraryAlbum, LibraryArtist, LibraryTrack
from app.routers.library import album_tracks, artist_albums, artists


async def test_browse_artist_albums_and_tracks(session: AsyncSession) -> None:
    session.add(LibraryArtist(id="artist-1", name="Daft Punk", album_count=1))
    session.add(LibraryArtist(id="artist-2", name="Air", album_count=1))
    session.add(
        LibraryAlbum(
            id="album-1",
            name="Discovery",
            artist="Daft Punk",
            artist_id="artist-1",
            cover_art="cover-1",
        )
    )
    session.add(
        LibraryAlbum(
            id="album-2",
            name="Moon Safari",
            artist="Air",
            artist_id="artist-2",
            cover_art="cover-2",
        )
    )
    session.add(
        LibraryTrack(
            id="song-1",
            title="One More Time",
            artist="Daft Punk",
            album="Discovery",
            album_id="album-1",
            cover_art="cover-1",
        )
    )
    session.add(
        LibraryTrack(
            id="song-2",
            title="La femme d'argent",
            artist="Air",
            album="Moon Safari",
            album_id="album-2",
            cover_art="cover-2",
        )
    )
    await session.commit()

    artist_rows = await artists(q="daft", limit=200, session=session)
    album_rows = await artist_albums("artist-1", session)
    track_rows = await album_tracks("album-1", session)

    assert [artist.name for artist in artist_rows] == ["Daft Punk"]
    assert [album.name for album in album_rows] == ["Discovery"]
    assert [track.title for track in track_rows] == ["One More Time"]
    assert track_rows[0].cover_url == "/api/library/cover?id=cover-1"
