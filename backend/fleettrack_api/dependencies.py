from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from fleettrack_api.core.config import Settings, get_settings
from fleettrack_api.core.errors import DependencyUnavailableError
from fleettrack_api.repositories.mongodb import MongoRepository
from fleettrack_api.repositories.postgres import PostgresRepository

logger = logging.getLogger(__name__)
HealthCheck = Callable[[], bool]


def get_postgres_repository(
    settings: Settings = Depends(get_settings),
) -> Iterator[PostgresRepository]:
    if not settings.database_url:
        raise DependencyUnavailableError("postgresql")
    connection = None
    try:
        connection = psycopg.connect(
            settings.database_url,
            connect_timeout=settings.database_connect_timeout,
            row_factory=dict_row,
        )
        yield PostgresRepository(connection)
    except psycopg.Error as exc:
        logger.warning(
            "PostgreSQL connection failed",
            extra={"event": "postgres_connection_failed", "error_type": type(exc).__name__},
        )
        raise DependencyUnavailableError("postgresql") from exc
    finally:
        if connection is not None:
            connection.close()


def get_mongo_repository(
    settings: Settings = Depends(get_settings),
) -> Iterator[MongoRepository]:
    if not settings.mongodb_uri:
        raise DependencyUnavailableError("mongodb")
    client = None
    try:
        client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_connect_timeout_ms,
            tz_aware=True,
        )
        collection: Collection = client[settings.mongodb_database][
            settings.mongodb_collection
        ]
        yield MongoRepository(collection)
    except PyMongoError as exc:
        logger.warning(
            "MongoDB connection failed",
            extra={"event": "mongodb_connection_failed", "error_type": type(exc).__name__},
        )
        raise DependencyUnavailableError("mongodb") from exc
    finally:
        if client is not None:
            client.close()


def get_postgres_health_check(
    settings: Settings = Depends(get_settings),
) -> HealthCheck:
    def check() -> bool:
        if not settings.database_url:
            return False
        try:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=settings.database_connect_timeout,
            ) as connection:
                connection.execute("SELECT 1")
            return True
        except psycopg.Error as exc:
            logger.warning(
                "PostgreSQL readiness check failed",
                extra={"event": "postgres_readiness_failed", "error_type": type(exc).__name__},
            )
            return False

    return check


def get_mongo_health_check(
    settings: Settings = Depends(get_settings),
) -> HealthCheck:
    def check() -> bool:
        if not settings.mongodb_uri:
            return False
        client = None
        try:
            client = MongoClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=settings.mongodb_connect_timeout_ms,
            )
            client.admin.command("ping")
            return True
        except PyMongoError as exc:
            logger.warning(
                "MongoDB readiness check failed",
                extra={"event": "mongodb_readiness_failed", "error_type": type(exc).__name__},
            )
            return False
        finally:
            if client is not None:
                client.close()

    return check
