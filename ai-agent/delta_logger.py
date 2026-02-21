from dotenv import load_dotenv
load_dotenv()

import logging
import os
from datetime import datetime, timezone
from databricks.sdk import WorkspaceClient


class DeltaLakeHandler(logging.Handler):

    def __init__(self, table_name="agent_logs"):
        super().__init__()
        self._table = table_name
        self._warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        self._client = WorkspaceClient(
            host=os.getenv("DATABRICKS_HOST"),
            token=os.getenv("DATABRICKS_TOKEN")
        )
        self._init_table()

    def _run_sql(self, sql):
        self._client.statement_execution.execute_statement(
            warehouse_id=self._warehouse_id,
            statement=sql,
            wait_timeout="30s"
        )

    def _init_table(self):
        self._run_sql(f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                ts      STRING,
                logger  STRING,
                level   STRING,
                message STRING
            )
            USING DELTA
        """)

    def emit(self, record):
        try:
            ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
            msg = self.format(record).replace("'", "\\'")
            logger = record.name.replace("'", "\\'")
            self._run_sql(f"""
                INSERT INTO {self._table} VALUES (
                    '{ts}',
                    '{logger}',
                    '{record.levelname}',
                    '{msg}'
                )
            """)
        except KeyboardInterrupt:
            raise
        except Exception:
            self.handleError(record)
