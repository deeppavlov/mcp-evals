"""DBA vector analysis: create and fill vector_analysis_* tables; verify against live catalog."""

import os
from pathlib import Path
from typing import Any

import anyio
import psycopg

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import PgConfig

from .custom_evaluator import AnalysisCoverageScenarioEvaluator, AnalysisTableSpec


class DbaVectorAnalysisTask(PostgresTask):
    """Task: analyze pgvector database, create vector_analysis_columns, vector_analysis_storage_consumption, vector_analysis_indices."""

    name = "dba_vector_analysis"
    goal = """PostgreSQL Vector Database Analysis

Analyze and optimize a pgvector-powered database to understand storage patterns, performance characteristics, and data quality for embeddings in production workloads.

## What you need to investigate

- Check vector extension status; identify all vector columns (columns, types, dimensions)
- Map the vector landscape: relationships between vector tables and regular tables
- Calculate vector storage overhead; analyze table sizes; understand growth patterns
- Catalog vector indexes (HNSW, IVFFlat); measure index effectiveness; identify optimization opportunities
- Hunt for data issues: NULL vectors, dimension mismatches, corrupted embeddings

## Your deliverables

Create these analysis tables and populate them with your findings:

### vector_analysis_columns

Complete catalog of every vector column:

```sql
CREATE TABLE vector_analysis_columns (
    schema VARCHAR(50),
    table_name VARCHAR(100),
    column_name VARCHAR(100),
    dimensions INTEGER,
    data_type VARCHAR(50),
    has_constraints BOOLEAN,
    rows BIGINT
);
```

### vector_analysis_storage_consumption

Show where storage is consumed:

```sql
CREATE TABLE vector_analysis_storage_consumption (
    schema VARCHAR(50),
    table_name VARCHAR(100),
    total_size_bytes BIGINT,
    vector_data_bytes BIGINT,
    regular_data_bytes BIGINT,
    vector_storage_pct NUMERIC(5,2),
    row_count BIGINT
);
```

### vector_analysis_indices

Document all vector indexes:

```sql
CREATE TABLE vector_analysis_indices (
    schema VARCHAR(50),
    table_name VARCHAR(100),
    column_name VARCHAR(100),
    index_name VARCHAR(100),
    index_type VARCHAR(50),
    index_size_bytes BIGINT
);
```

Use PostgreSQL system catalogs and pgvector to gather metrics about the vector database implementation.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=None)
        self.evaluators = (
            AnalysisCoverageScenarioEvaluator(
                analysis_specs=[
                    AnalysisTableSpec(
                        table_name="vector_analysis_columns",
                        expected_columns=[
                            "column_name",
                            "data_type",
                            "dimensions",
                            "has_constraints",
                            "rows",
                            "schema",
                            "table_name",
                        ],
                        catalog_query="""
                            SELECT table_name, column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND data_type = 'USER-DEFINED'
                              AND udt_name = 'vector'
                            ORDER BY table_name, column_name
                        """,
                        analysis_columns_query="""
                            SELECT table_name, column_name
                            FROM vector_analysis_columns
                            ORDER BY table_name, column_name
                        """,
                    ),
                    AnalysisTableSpec(
                        table_name="vector_analysis_storage_consumption",
                        expected_columns=[
                            "column_name",
                            "regular_data_bytes",
                            "row_count",
                            "schema",
                            "table_name",
                            "total_size_bytes",
                            "vector_data_bytes",
                            "vector_storage_pct",
                        ],
                        catalog_query="""
                            SELECT table_name, table_name AS column_name
                            FROM (
                                SELECT DISTINCT table_name
                                FROM information_schema.columns
                                WHERE table_schema = 'public'
                                  AND data_type = 'USER-DEFINED'
                                  AND udt_name = 'vector'
                            ) t
                            ORDER BY table_name
                        """,
                        analysis_columns_query="""
                            SELECT table_name, table_name AS column_name
                            FROM vector_analysis_storage_consumption
                            ORDER BY table_name
                        """,
                    ),
                    AnalysisTableSpec(
                        table_name="vector_analysis_indices",
                        expected_columns=[
                            "column_name",
                            "index_name",
                            "index_size_bytes",
                            "index_type",
                            "schema",
                            "table_name",
                        ],
                        catalog_query="""
                            SELECT tablename AS table_name, indexname AS column_name
                            FROM pg_indexes
                            WHERE schemaname = 'public'
                              AND (indexdef ILIKE '%hnsw%' OR indexdef ILIKE '%ivfflat%')
                              AND tablename NOT LIKE '%analysis%'
                            ORDER BY tablename, indexname
                        """,
                        analysis_columns_query="""
                            SELECT table_name, index_name AS column_name
                            FROM vector_analysis_indices
                            ORDER BY table_name, index_name
                        """,
                    ),
                ],
                allowed_analysis_tables=[
                    "vector_analysis_columns",
                    "vector_analysis_storage_consumption",
                    "vector_analysis_indices",
                ],
                analysis_table_pattern="vector_analysis_%",
            ),
        )

    async def prepare_init(self, conn: psycopg.AsyncConnection[Any], db_name: str) -> None:
        """Run mcpmark vectors_setup.prepare_vector_environment() targeting the task DB."""
        cfg = self._pg_config
        env = {
            **os.environ,
            "POSTGRES_HOST": cfg.host,
            "POSTGRES_PORT": str(cfg.port),
            "POSTGRES_USERNAME": cfg.user,
            "POSTGRES_PASSWORD": cfg.password,
            "POSTGRES_DATABASE": db_name,
        }
        project_root = Path(__file__).resolve().parents[6]
        mcpmark_parent = str(project_root)
        env["MCP_EVALS_PROJECT_ROOT"] = mcpmark_parent
        import_code = """
import os
import sys
sys.path.insert(0, os.environ["MCP_EVALS_PROJECT_ROOT"])
from mcpmark.tasks.postgres.standard.vectors.vectors_setup import prepare_vector_environment
prepare_vector_environment()
"""
        proc = await anyio.open_process(
            ["python", "-c", import_code],
            env=env,
            stdout=anyio.process.PIPE,
            stderr=anyio.process.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            msg = f"vectors_setup failed (exit {proc.returncode}): stderr={stderr.decode() if stderr else ''}"
            raise RuntimeError(msg)
