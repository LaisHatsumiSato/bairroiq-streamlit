import unittest

from bairroiq.databricks import DatabricksConfig


class DatabricksConfigTests(unittest.TestCase):
    def test_config_builds_qualified_table_names(self) -> None:
        config = DatabricksConfig.from_sources(
            {
                "databricks": {
                    "server_hostname": "workspace.example.com",
                    "http_path": "/sql/1.0/warehouses/demo",
                    "access_token": "test-token",
                    "catalog": "main",
                    "schema": "default",
                    "metrics_table": "neighborhood_metrics",
                    "history_table": "analytics.neighborhood_history",
                }
            },
            environ={},
        )

        self.assertEqual(config.metrics_table, "`main`.`default`.`neighborhood_metrics`")
        self.assertEqual(config.history_table, "`main`.`analytics`.`neighborhood_history`")

    def test_table_names_reject_sql_fragments(self) -> None:
        with self.assertRaisesRegex(ValueError, "identificadores SQL"):
            DatabricksConfig.from_sources(
                {
                    "server_hostname": "workspace.example.com",
                    "http_path": "/sql/1.0/warehouses/demo",
                    "access_token": "test-token",
                    "catalog": "main",
                    "schema": "default",
                    "metrics_table": "metrics; DROP TABLE users",
                    "history_table": "history",
                },
                environ={},
            )


if __name__ == "__main__":
    unittest.main()
