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

    def __init__(self, pg_config: PgConfig, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=None, tool_retries=tool_retries)
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
