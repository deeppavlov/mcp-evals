"""Create monthly_sales_summary and top_music_charts in the Chinook database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# --- monthly_sales_summary ---
MONTHLY_SALES_QUERY = """
SELECT year_month, total_sales, invoice_count, avg_invoice_total
FROM monthly_sales_summary
ORDER BY year_month
"""
MONTHLY_SALES_EXPECTED = """
SELECT
    TO_CHAR("InvoiceDate", 'YYYY-MM') AS year_month,
    COALESCE(SUM("Total"), 0)::DECIMAL AS total_sales,
    COUNT(*)::BIGINT AS invoice_count,
    AVG("Total")::DECIMAL AS avg_invoice_total
FROM "Invoice"
GROUP BY TO_CHAR("InvoiceDate", 'YYYY-MM')
ORDER BY year_month
"""

# --- top_music_charts ---
TOP_MUSIC_QUERY = """
SELECT * FROM top_music_charts
ORDER BY chart_type, rank
"""
TOP_MUSIC_EXPECTED = """
WITH track_revenue AS (
    SELECT
        t."TrackId",
        t."Name" AS track_name,
        a."Title" AS album_title,
        ar."Name" AS artist_name,
        COALESCE(SUM(il."UnitPrice" * il."Quantity"), 0) AS revenue
    FROM "Track" t
    JOIN "Album" a ON a."AlbumId" = t."AlbumId"
    JOIN "Artist" ar ON ar."ArtistId" = a."ArtistId"
    LEFT JOIN "InvoiceLine" il ON il."TrackId" = t."TrackId"
    GROUP BY t."TrackId", t."Name", a."Title", ar."Name"
),
ranked AS (
    SELECT
        'track' AS chart_type,
        track_name AS name,
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC NULLS LAST)::INT AS rank
    FROM track_revenue
    UNION ALL
    SELECT
        'album',
        album_title,
        SUM(revenue),
        ROW_NUMBER() OVER (ORDER BY SUM(revenue) DESC NULLS LAST)::INT
    FROM track_revenue
    GROUP BY album_title
    UNION ALL
    SELECT
        'artist',
        artist_name,
        SUM(revenue),
        ROW_NUMBER() OVER (ORDER BY SUM(revenue) DESC NULLS LAST)::INT
    FROM track_revenue
    GROUP BY artist_name
)
SELECT chart_type, name, revenue, rank FROM ranked
ORDER BY chart_type, rank
"""


class SalesAndMusicChartsTask(PostgresTask):
    """Task: create monthly_sales_summary and top_music_charts from Invoice/InvoiceLine/Track/Album/Artist."""

    name = "sales_and_music_charts"
    goal = """Create reporting objects for sales and music charts in the Chinook database.

## Your Task

1. **monthly_sales_summary** — Create a table or materialized view that aggregates invoice data by month:
   - year_month (e.g. 'YYYY-MM')
   - total_sales (sum of Invoice.Total)
   - invoice_count
   - avg_invoice_total

2. **top_music_charts** — Create a table or view that ranks tracks, albums, and artists by revenue (from InvoiceLine \
joined to Track/Album/Artist):
   - chart_type ('track', 'album', 'artist')
   - name (track name, album title, or artist name)
   - revenue (sum of UnitPrice * Quantity)
   - rank (row number by revenue descending)

Use the existing tables: "Invoice", "InvoiceLine", "Track", "Album", "Artist". Populate or refresh the objects so \
they contain current data.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.CHI)
        self.evaluators = (
            SqlResultMatches(
                MONTHLY_SALES_QUERY,
                expected_query=MONTHLY_SALES_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
            SqlResultMatches(
                TOP_MUSIC_QUERY,
                expected_query=TOP_MUSIC_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
