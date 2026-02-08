# ruff: noqa: S311

"""In-process vector DB setup for dba_vector_analysis (no mcpmark dependency)."""

from __future__ import annotations

import contextlib
import json
import random
from typing import Any

import psycopg


def _generate_mock_embedding(dimensions: int = 1536) -> list[float]:
    """Generate a unit-norm mock embedding (pure Python, no numpy)."""
    values = [random.uniform(-1.0, 1.0) for _ in range(dimensions)]
    norm = sum(x * x for x in values) ** 0.5
    if norm > 0:
        values = [x / norm for x in values]
    return values


def _vector_to_literal(vec: list[float]) -> str:
    """Format embedding as PostgreSQL vector literal for %s::vector."""
    return "[" + ",".join(str(x) for x in vec) + "]"


async def prepare_vector_environment(  # noqa: C901, PLR0912, PLR0915
    conn: psycopg.AsyncConnection[Any],
) -> None:
    """Create pgvector extension, tables, sample data, and indexes.

    Parity with mcpmark vectors_setup.
    """
    async with conn.cursor() as cur:
        await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        await cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                document_type VARCHAR(50) DEFAULT 'article',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER,
                embedding vector(1536)
            );
        """)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_size INTEGER,
                overlap_size INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding vector(1536)
            );
        """)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS user_queries (
                id SERIAL PRIMARY KEY,
                query_text TEXT NOT NULL,
                user_id VARCHAR(100),
                session_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms INTEGER,
                embedding vector(1536)
            );
        """)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS embedding_models (
                id SERIAL PRIMARY KEY,
                model_name VARCHAR(100) NOT NULL UNIQUE,
                provider VARCHAR(50) NOT NULL,
                dimensions INTEGER NOT NULL,
                max_tokens INTEGER,
                cost_per_token DECIMAL(10, 8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                kb_name VARCHAR(100) NOT NULL,
                description TEXT,
                domain VARCHAR(50),
                language VARCHAR(10) DEFAULT 'en',
                total_documents INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0,
                total_storage_mb DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id SERIAL PRIMARY KEY,
                query_hash VARCHAR(64) NOT NULL,
                query_text TEXT NOT NULL,
                results_json JSONB,
                result_count INTEGER,
                search_time_ms INTEGER,
                similarity_threshold DECIMAL(4, 3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """)

    async with conn.cursor() as cur:
        embedding_models = [
            ("text-embedding-3-small", "OpenAI", 1536, 8192, 0.00000002, True),
            ("text-embedding-3-large", "OpenAI", 3072, 8192, 0.00000013, True),
            ("text-embedding-ada-002", "OpenAI", 1536, 8192, 0.00000010, False),
            ("all-MiniLM-L6-v2", "Sentence-Transformers", 384, 512, 0.0, True),
            ("all-mpnet-base-v2", "Sentence-Transformers", 768, 514, 0.0, True),
        ]
        for row in embedding_models:
            await cur.execute(
                """
                INSERT INTO embedding_models (model_name, provider, dimensions, max_tokens, cost_per_token, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_name) DO NOTHING;
                """,
                row,
            )

        knowledge_bases = [
            ("Technical Documentation", "Software engineering and API documentation", "technology"),
            ("Research Papers", "Academic papers and research publications", "research"),
            ("Customer Support", "FAQ and troubleshooting guides", "support"),
            ("Product Catalog", "Product descriptions and specifications", "commerce"),
            ("Legal Documents", "Contracts, policies, and legal texts", "legal"),
        ]
        for kb_name, description, domain in knowledge_bases:
            total_docs = random.randint(50, 500)
            total_chunks = random.randint(200, 2000)
            total_storage = round(random.uniform(10.5, 250.8), 2)
            await cur.execute(
                """
                INSERT INTO knowledge_base (
                    kb_name, description, domain, total_documents, total_chunks,
                    total_storage_mb
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (kb_name, description, domain, total_docs, total_chunks, total_storage),
            )
            await cur.fetchone()

        sample_documents = [
            (
                "PostgreSQL Performance Tuning",
                "Comprehensive guide to optimizing PostgreSQL database performance "
                "including indexing strategies, query optimization, and configuration tuning.",
                "https://example.com/pg-performance",
                "technical_guide",
            ),
            (
                "Vector Similarity Search",
                "Understanding vector embeddings and similarity search algorithms "
                "for AI applications and recommendation systems.",
                "https://example.com/vector-search",
                "technical_guide",
            ),
            (
                "RAG Implementation Best Practices",
                "Best practices for implementing Retrieval-Augmented Generation "
                "systems using vector databases and large language models.",
                "https://example.com/rag-practices",
                "best_practices",
            ),
            (
                "Database Security Guidelines",
                "Security considerations and implementation guidelines for "
                "PostgreSQL databases in production environments.",
                "https://example.com/db-security",
                "security_guide",
            ),
            (
                "Machine Learning with SQL",
                "Integrating machine learning workflows with SQL databases and "
                "leveraging database extensions for AI applications.",
                "https://example.com/ml-sql",
                "tutorial",
            ),
            (
                "API Documentation Standards",
                "Standards and best practices for creating comprehensive and "
                "user-friendly API documentation.",
                "https://example.com/api-docs",
                "documentation",
            ),
            (
                "Microservices Architecture",
                "Design patterns and implementation strategies for microservices "
                "architecture in modern applications.",
                "https://example.com/microservices",
                "architecture_guide",
            ),
            (
                "Data Pipeline Optimization",
                "Optimizing data processing pipelines for scalability, reliability, "
                "and performance in enterprise environments.",
                "https://example.com/data-pipelines",
                "optimization_guide",
            ),
            (
                "Cloud Database Migration",
                "Step-by-step guide for migrating on-premises databases to cloud "
                "infrastructure with minimal downtime.",
                "https://example.com/cloud-migration",
                "migration_guide",
            ),
            (
                "NoSQL vs SQL Comparison",
                "Detailed comparison of NoSQL and SQL databases, including use "
                "cases, performance characteristics, and selection criteria.",
                "https://example.com/nosql-sql",
                "comparison_guide",
            ),
        ]
        doc_ids = []
        for title, content, url, doc_type in sample_documents:
            word_count = len(content.split())
            embedding_str = _vector_to_literal(_generate_mock_embedding(1536))
            await cur.execute(
                """
                INSERT INTO documents (title, content, source_url, document_type, word_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
                RETURNING id;
                """,
                (title, content, url, doc_type, word_count, embedding_str),
            )
            one: Any | tuple[Any, ...] | None = await cur.fetchone()
            if one is None:
                raise RuntimeError("INSERT ... RETURNING id did not return a row")
            doc_ids.append(one[0])

        for doc_id in doc_ids:
            num_chunks = random.randint(3, 7)
            for chunk_idx in range(num_chunks):
                chunk_text = (
                    f"This is chunk {chunk_idx + 1} of document {doc_id}. "
                    "It contains relevant information that would be useful for similarity search and RAG applications. "
                    "The content includes technical details, examples, and best practices."
                )
                chunk_size = len(chunk_text)
                overlap_size = random.randint(20, 50) if chunk_idx > 0 else 0
                embedding_str = _vector_to_literal(_generate_mock_embedding(1536))
                await cur.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, chunk_text, chunk_size,
                        overlap_size, embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::vector);
                    """,
                    (doc_id, chunk_idx, chunk_text, chunk_size, overlap_size, embedding_str),
                )

        sample_queries = [
            ("How to optimize PostgreSQL performance?", "user123", "session_abc1"),
            ("What are vector embeddings?", "user456", "session_def2"),
            ("Best practices for RAG implementation", "user789", "session_ghi3"),
            ("Database security checklist", "user123", "session_abc2"),
            ("Machine learning with databases", "user456", "session_def3"),
            ("API documentation examples", "user321", "session_jkl1"),
            ("Microservices design patterns", "user654", "session_mno2"),
            ("Data pipeline best practices", "user987", "session_pqr3"),
            ("Cloud migration strategies", "user111", "session_stu4"),
            ("NoSQL vs SQL databases", "user222", "session_vwx5"),
        ]
        for query_text, user_id, session_id in sample_queries:
            embedding_str = _vector_to_literal(_generate_mock_embedding(1536))
            response_time = random.randint(50, 500)
            await cur.execute(
                """
                INSERT INTO user_queries (query_text, user_id, session_id, response_time_ms, embedding)
                VALUES (%s, %s, %s, %s, %s::vector);
                """,
                (query_text, user_id, session_id, response_time, embedding_str),
            )

        num_docs = len(doc_ids)
        for i in range(5):
            query_hash = f"hash_{random.randint(100000, 999999)}"
            query_text = f"Sample cached query {i + 1}"
            results = [
                {
                    "doc_id": random.randint(1, num_docs),
                    "similarity": round(random.uniform(0.7, 0.95), 3),
                }
                for _ in range(3)
            ]
            result_count = len(results)
            search_time = random.randint(10, 100)
            threshold = round(random.uniform(0.6, 0.8), 3)
            await cur.execute(
                """
                INSERT INTO search_cache (
                    query_hash, query_text, results_json, result_count,
                    search_time_ms, similarity_threshold
                )
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (query_hash, query_text, json.dumps(results), result_count, search_time, threshold),
            )

    async with conn.cursor() as cur:
        vector_indexes = [
            ("documents_embedding_idx", "documents", "embedding", "hnsw"),
            ("chunks_embedding_idx", "document_chunks", "embedding", "hnsw"),
            ("queries_embedding_idx", "user_queries", "embedding", "hnsw"),
        ]
        for idx_name, table_name, column_name, method in vector_indexes:
            try:
                if method == "hnsw":
                    await cur.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS {idx_name}
                        ON {table_name} USING hnsw ({column_name} vector_cosine_ops);
                        """
                    )
                else:
                    await cur.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS {idx_name}
                        ON {table_name} USING ivfflat ({column_name} vector_cosine_ops)
                        WITH (lists = 100);
                        """
                    )
            except psycopg.Error:
                if method == "hnsw":
                    with contextlib.suppress(psycopg.Error):
                        await cur.execute(
                            f"""
                            CREATE INDEX IF NOT EXISTS {idx_name}_ivf
                            ON {table_name} USING ivfflat ({column_name} vector_cosine_ops)
                            WITH (lists = 100);
                            """
                        )

        regular_indexes = [
            ("documents_title_idx", "documents", "title"),
            ("documents_type_idx", "documents", "document_type"),
            ("documents_created_idx", "documents", "created_at"),
            ("chunks_doc_id_idx", "document_chunks", "document_id"),
            ("chunks_index_idx", "document_chunks", "chunk_index"),
            ("queries_user_idx", "user_queries", "user_id"),
            ("queries_created_idx", "user_queries", "created_at"),
            ("cache_hash_idx", "search_cache", "query_hash"),
            ("cache_expires_idx", "search_cache", "expires_at"),
        ]
        for idx_name, table_name, column_name in regular_indexes:
            with contextlib.suppress(psycopg.Error):
                await cur.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({column_name});"
                )
