from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _read_table(connection: Any, table_name: str) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        column_names = [column[0] for column in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=column_names)


@dataclass(frozen=True)
class DatabricksConfig:
    server_hostname: str
    http_path: str
    access_token: str
    metrics_table: str
    history_table: str

    @classmethod
    def from_sources(
        cls,
        secrets: Mapping[str, Any] | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> DatabricksConfig:
        environment = os.environ if environ is None else environ
        secret_values: Mapping[str, Any] = {}
        if secrets is not None:
            section = secrets.get("databricks", secrets)
            if isinstance(section, Mapping):
                secret_values = section

        def setting(name: str, secret_name: str | None = None) -> str:
            value = environment.get(f"DATABRICKS_{name.upper()}")
            if not value:
                value = secret_values.get(secret_name or name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Configuração Databricks ausente: DATABRICKS_{name.upper()} "
                    f"ou [databricks].{secret_name or name}."
                )
            return value.strip()

        catalog = setting("catalog", "catalog")
        schema = setting("schema", "schema")
        metrics_table = setting("metrics_table", "metrics_table")
        history_table = setting("history_table", "history_table")
        return cls(
            server_hostname=setting("server_hostname", "server_hostname"),
            http_path=setting("http_path", "http_path"),
            access_token=setting("access_token", "access_token"),
            metrics_table=_qualified_table(catalog, schema, metrics_table),
            history_table=_qualified_table(catalog, schema, history_table),
        )


def _qualified_table(catalog: str, schema: str, table: str) -> str:
    parts = table.split(".") if "." in table else [catalog, schema, table]
    if not 1 <= len(parts) <= 3 or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(
            "Os nomes das tabelas Databricks devem conter apenas identificadores SQL "
            "simples, separados por pontos."
        )
    if len(parts) == 1:
        parts = [catalog, schema, parts[0]]
    elif len(parts) == 2:
        parts = [catalog, *parts]
    return ".".join(f"`{part}`" for part in parts)


class DatabricksDataProvider:
    def __init__(self, config: DatabricksConfig) -> None:
        self._config = config

    def _connect(self) -> Any:
        try:
            from databricks import sql
        except ImportError as exc:
            raise RuntimeError(
                "Conector Databricks ausente. Instale requirements-databricks.txt."
            ) from exc

        return sql.connect(
            server_hostname=self._config.server_hostname,
            http_path=self._config.http_path,
            access_token=self._config.access_token,
        )

    def load_metrics(self) -> pd.DataFrame:
        with self._connect() as connection:
            return _read_table(connection, self._config.metrics_table)

    def load_history(self) -> pd.DataFrame:
        with self._connect() as connection:
            return _read_table(connection, self._config.history_table)
