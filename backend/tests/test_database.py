"""Tests des migrations légères appliquées aux bases SQLite existantes."""

from sqlalchemy import create_engine, inspect

from app.database import _migrate_sqlite


def test_sqlite_migration_adds_cover_columns() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE library_tracks (id VARCHAR(128) PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE library_albums (id VARCHAR(128) PRIMARY KEY)")
        _migrate_sqlite(conn)

        inspector = inspect(conn)
        track_columns = {column["name"] for column in inspector.get_columns("library_tracks")}
        album_columns = {column["name"] for column in inspector.get_columns("library_albums")}
        assert "cover_art" in track_columns
        assert "cover_art" in album_columns

    engine.dispose()
