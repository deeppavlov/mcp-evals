"""DBA vector analysis: create and fill vector_analysis_* tables; verify against live catalog."""

from typing import Any

import psycopg

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import PgConfig

from ._setup import prepare_vector_environment
from .custom_evaluator import AnalysisCoverageScenarioEvaluator, AnalysisTableSpec


class DbaVectorAnalysisTask(PostgresTask):
    """Task: analyze pgvector database, create vector_analysis_* tables; verify against live catalog.

    Creates vector_analysis_columns, vector_analysis_storage_consumption, vector_analysis_indices.
    """

    name = "dba_vector_analysis"
    goal = """# PostgreSQL Vector Database Analysis

> Analyze and optimize a pgvector-powered database to understand storage patterns, performance characteristics, and \
data quality for embeddings in production workloads.

## What's this about?

You've got a PostgreSQL database running with the vector extension that stores embeddings for RAG (document similarity \
search, image recognition), or other ML workloads.
Your job is to dive deep into this vector database and figure out what's going on under the hood.
You need to understand:

- how vectors are stored
- how much space they're taking up
- whether indexes are working properly
- if there are any data quality issues lurking around

## What you need to investigate

First, get familiar with what you're working with:

- Check vector extension status: ensuring it's installed properly, check version, identify any configuration \
issues
- Identify all vector columns across entire database: providing me columns, types of columns, and vector dim \
(dimensions)
- Map the vector landscape: understand relationships between vector tables and regular tables, foreign keys, \
dependencies

Vectors can eat up a lot of storage, so let's see where the bytes are going:

- Calculate vector storage overhead: measure how much space vectors take compared to regular columns in same tables
- Analyze table sizes: identify which vector tables are biggest storage consumers, break down by table
- Understand growth patterns: examine record counts and project future storage needs based on current data

Vectors without proper indexes are painfully slow, so investigate:

- Catalog vector indexes: find all HNSW and IVFFlat indexes, document their configurations and parameters
- Measure index effectiveness: determine if indexes are actually being used and helping query performance
- Identify optimization opportunities: spot missing indexes, suboptimal configurations, unused indexes

Bad vector data makes everything worse:

- Hunt for data issues: locate NULL vectors, dimension mismatches, corrupted embeddings that could break queries
- Validate consistency: ensure vectors in each column have consistent dimensions across all rows
- Check for outliers: find vectors that might be skewing similarity calculations or causing performance issues

## Your deliverables

Create these analysis tables and populate them with your findings:

### vector_analysis_columns

Complete catalog of every vector column you find:

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

Show exactly where storage is being consumed:

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

Document all vector indexes and their characteristics:
```sql
CREATE TABLE vector_analysis_indices (
    schema VARCHAR(50),
    table_name VARCHAR(100),
    column_name VARCHAR(100),
    index_name VARCHAR(100),
    index_type VARCHAR(50), -- 'hnsw', 'ivfflat', etc.
    index_size_bytes BIGINT
);
```

Use PostgreSQL system catalogs, pgvector-specific views, and storage analysis functions to gather comprehensive \
metrics about the vector database implementation.
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
                        allow_extra_rows=True,
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
                allowed_extra_analysis_prefixes=["expected_", "vector_analysis_results"],
            ),
        )

    async def prepare_init(self, conn: psycopg.AsyncConnection[Any], db_name: str) -> None:  # noqa: ARG002
        """Create pgvector extension, vector tables, sample data, and indexes (no mcpmark dependency)."""
        await prepare_vector_environment(conn)
