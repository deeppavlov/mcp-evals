"""RLS business access: social platform with Users, Posts, Comments, Channels.

channel moderators.
"""

from typing import Any, ClassVar

import psycopg
from psycopg import sql

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import PgConfig

from .custom_evaluator import RlsAssertion, RlsScenarioEvaluator


class RlsBusinessAccessTask(PostgresTask):
    """Task: implement RLS for social platform with proper access control for posts, comments, channels."""

    name = "rls_business_access"

    RLS_TABLES: ClassVar[list[str]] = ["users", "channels", "channel_moderators", "posts", "comments"]

    RLS_ASSERTIONS: ClassVar[list[RlsAssertion]] = [
        # Alice updates own profile (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=(
                "UPDATE users SET email = 'alice.updated@example.com' WHERE id = '11111111-1111-1111-1111-111111111111'"
            ),
            should_affect_rows=True,
        ),
        # Alice updates Bob's profile (block)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=(
                "UPDATE users SET email = 'bob.hacked@example.com' WHERE id = '22222222-2222-2222-2222-222222222222'"
            ),
            should_affect_rows=False,
        ),
        # Alice (owner) updates channel (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=(
                "UPDATE channels SET description = 'Updated by Alice' WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"
            ),
            should_affect_rows=True,
        ),
        # Charlie updates Alice's channel (block)
        RlsAssertion(
            set_session="SET app.current_user_id = '33333333-3333-3333-3333-333333333333'",
            run_sql=(
                "UPDATE channels SET description = 'Hacked by Charlie' "
                "WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"
            ),
            should_affect_rows=False,
        ),
        # Alice updates own post (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=("UPDATE posts SET title = 'Updated by Alice' WHERE id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'"),
            should_affect_rows=True,
        ),
        # Bob (moderator) updates Alice's post (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '22222222-2222-2222-2222-222222222222'",
            run_sql=("UPDATE posts SET content = 'Moderated by Bob' WHERE id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'"),
            should_affect_rows=True,
        ),
        # Eve updates Alice's post (block)
        RlsAssertion(
            set_session="SET app.current_user_id = '55555555-5555-5555-5555-555555555555'",
            run_sql=("UPDATE posts SET content = 'Hacked by Eve' WHERE id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'"),
            should_affect_rows=False,
        ),
        # Bob updates own comment (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '22222222-2222-2222-2222-222222222222'",
            run_sql=(
                "UPDATE comments SET content = 'Updated by Bob himself' "
                "WHERE id = '99999999-9999-9999-9999-999999999999'"
            ),
            should_affect_rows=True,
        ),
        # Alice (post author) updates Bob's comment (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=(
                "UPDATE comments SET content = 'Moderated by post author Alice' "
                "WHERE id = '99999999-9999-9999-9999-999999999999'"
            ),
            should_affect_rows=True,
        ),
        # Alice (owner) adds moderator (succeed)
        RlsAssertion(
            set_session="SET app.current_user_id = '11111111-1111-1111-1111-111111111111'",
            run_sql=(
                "INSERT INTO channel_moderators (channel_id, user_id) VALUES "
                "('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', "
                "'33333333-3333-3333-3333-333333333333')"
            ),
            should_affect_rows=True,
        ),
        # Charlie adds self as moderator to Bob's channel (block)
        RlsAssertion(
            set_session="SET app.current_user_id = '33333333-3333-3333-3333-333333333333'",
            run_sql=(
                "INSERT INTO channel_moderators (channel_id, user_id) VALUES "
                "('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', "
                "'33333333-3333-3333-3333-333333333333')"
            ),
            should_affect_rows=False,
        ),
    ]

    def __init__(self, pg_config: PgConfig, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=None, tool_retries=tool_retries)
        self.evaluators = (
            RlsScenarioEvaluator(
                tables_with_rls=self.RLS_TABLES,
                assertions=self.RLS_ASSERTIONS,
                rls_test_user="test_user",
                rls_test_password="testpass",  # noqa: S106
                content_visibility=(
                    "11111111-1111-1111-1111-111111111111",
                    "55555555-5555-5555-5555-555555555555",
                    2,
                    1,
                ),
                anonymous_user_check=True,
            ),
        )

    async def prepare_init(self, conn: psycopg.AsyncConnection[Any], db_name: str) -> None:
        """Create schema, helper functions, sample data, and test_user (mcpmark prepare_environment parity)."""
        async with conn.cursor() as cur:
            # Tables
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    is_public BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    is_public BOOLEAN DEFAULT true,
                    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS channel_moderators (
                    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel_id, user_id)
                );
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
                    author_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(200) NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
                    author_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Helper functions
            await cur.execute("""
                CREATE OR REPLACE FUNCTION app_current_user_id()
                RETURNS UUID AS $$
                BEGIN
                    RETURN NULLIF(current_setting('app.current_user_id', true), '')::UUID;
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;
            """)
            await cur.execute("""
                CREATE OR REPLACE FUNCTION is_channel_owner(p_channel_id UUID, p_user_id UUID)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN EXISTS (
                        SELECT 1 FROM channels
                        WHERE id = p_channel_id AND owner_id = p_user_id
                    );
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;
            """)
            await cur.execute("""
                CREATE OR REPLACE FUNCTION is_channel_moderator(p_channel_id UUID, p_user_id UUID)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN EXISTS (
                        SELECT 1 FROM channel_moderators
                        WHERE channel_id = p_channel_id AND user_id = p_user_id
                    );
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;
            """)
            await cur.execute("""
                CREATE OR REPLACE FUNCTION can_moderate_channel(p_channel_id UUID, p_user_id UUID)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN is_channel_owner(p_channel_id, p_user_id)
                           OR is_channel_moderator(p_channel_id, p_user_id);
                END;
                $$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;
            """)
            # Sample data (exact UUIDs for mcpmark parity)
            await cur.execute("""
                INSERT INTO users (id, username, email, is_public) VALUES
                ('11111111-1111-1111-1111-111111111111', 'alice', 'alice@example.com', true),
                ('22222222-2222-2222-2222-222222222222', 'bob', 'bob@example.com', true),
                ('33333333-3333-3333-3333-333333333333', 'charlie', 'charlie@example.com', false),
                ('44444444-4444-4444-4444-444444444444', 'diana', 'diana@example.com', true),
                ('55555555-5555-5555-5555-555555555555', 'eve', 'eve@example.com', false)
                ON CONFLICT (id) DO NOTHING;
            """)
            await cur.execute("""
                INSERT INTO channels (id, name, description, is_public, owner_id)
                VALUES
                ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'general',
                 'General discussion channel', true, '11111111-1111-1111-1111-111111111111'),
                ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'tech-talk',
                 'Technical discussions', true, '22222222-2222-2222-2222-222222222222'),
                ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'random',
                 'Random conversations', false, '33333333-3333-3333-3333-333333333333')
                ON CONFLICT (id) DO NOTHING;
            """)
            await cur.execute("""
                INSERT INTO channel_moderators (channel_id, user_id) VALUES
                ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222'),
                ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '44444444-4444-4444-4444-444444444444')
                ON CONFLICT (channel_id, user_id) DO NOTHING;
            """)
            await cur.execute("""
                INSERT INTO posts (id, channel_id, author_id, title, content)
                VALUES
                ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                 '11111111-1111-1111-1111-111111111111', 'Welcome to the platform!',
                 'This is our first post'),
                ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                 '33333333-3333-3333-3333-333333333333', 'Hello everyone', 'Nice to meet you all'),
                ('ffffffff-ffff-ffff-ffff-ffffffffffff', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
                 '22222222-2222-2222-2222-222222222222', 'PostgreSQL RLS Tutorial',
                 'Let''s discuss Row Level Security'),
                ('10101010-1010-1010-1010-101010101010', 'cccccccc-cccc-cccc-cccc-cccccccccccc',
                 '55555555-5555-5555-5555-555555555555', 'Random thoughts',
                 'Just some random content here')
                ON CONFLICT (id) DO NOTHING;
            """)
            await cur.execute("""
                INSERT INTO comments (id, post_id, author_id, content) VALUES
                ('99999999-9999-9999-9999-999999999999', 'dddddddd-dddd-dddd-dddd-dddddddddddd',
                 '22222222-2222-2222-2222-222222222222', 'Great to have you here!'),
                ('88888888-8888-8888-8888-888888888888', 'dddddddd-dddd-dddd-dddd-dddddddddddd',
                 '33333333-3333-3333-3333-333333333333', 'Thanks for setting this up'),
                ('77777777-7777-7777-7777-777777777777', 'ffffffff-ffff-ffff-ffff-ffffffffffff',
                 '44444444-4444-4444-4444-444444444444', 'RLS is really powerful!'),
                ('66666666-6666-6666-6666-666666666666', 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
                 '11111111-1111-1111-1111-111111111111', 'Welcome Charlie!')
                ON CONFLICT (id) DO NOTHING;
            """)
            # Indexes
            await cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_channels_owner_id ON channels(owner_id);
                CREATE INDEX IF NOT EXISTS idx_channels_is_public ON channels(is_public);
                CREATE INDEX IF NOT EXISTS idx_channel_moderators_channel_user
                    ON channel_moderators(channel_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_channel_moderators_user ON channel_moderators(user_id);
                CREATE INDEX IF NOT EXISTS idx_posts_channel_id ON posts(channel_id);
                CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
                CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
                CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
                CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
                CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);
                CREATE INDEX IF NOT EXISTS idx_users_is_public ON users(is_public);
            """)
            # Create test_user and grant permissions (for RLS verification)
            await cur.execute("""
                DO $$
                BEGIN
                  CREATE ROLE test_user LOGIN PASSWORD 'testpass';
                EXCEPTION
                  WHEN duplicate_object THEN NULL;
                END
                $$;
            """)
        # Use separate connection for DB-level grant (must run outside transaction)
        async with conn.cursor() as cur:
            await cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO test_user").format(sql.Identifier(db_name)))
            await cur.execute("GRANT USAGE ON SCHEMA public TO test_user")
            await cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_user")
            await cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO test_user")
            await cur.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO test_user")
