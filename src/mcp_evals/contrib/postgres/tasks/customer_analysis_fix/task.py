"""Fix buggy customer analysis query and create customer_analysis_fixed table in dvdrental."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Full 13-column output (mcpmark parity): customer_id, customer_name, city, country,
# total_rentals, unique_films, total_spent, favorite_category, favorite_actor,
# avg_rental_duration, customer_tier, most_popular_film_in_region, regional_film_rental_count
CUSTOMER_ANALYSIS_QUERY = """
SELECT customer_id, customer_name, city, country, total_rentals, unique_films,
       total_spent, favorite_category, favorite_actor, avg_rental_duration,
       customer_tier, most_popular_film_in_region, regional_film_rental_count
FROM customer_analysis_fixed
ORDER BY customer_id
"""

# Ground truth: full CTE logic matching mcpmark (paid_rentals, basic stats, categories, actors, regional)
CUSTOMER_ANALYSIS_EXPECTED = """
WITH paid_rentals AS (
    SELECT
        p.customer_id,
        COUNT(DISTINCT p.rental_id)::BIGINT AS total_rentals,
        COALESCE(SUM(p.amount), 0)::DECIMAL AS total_spent
    FROM payment p
    GROUP BY p.customer_id
),
customer_basic_stats AS (
    SELECT
        c.customer_id,
        (c.first_name || ' ' || c.last_name) AS customer_name,
        ci.city,
        co.country,
        ci.country_id,
        pr.total_rentals,
        pr.total_spent,
        (
            SELECT COUNT(DISTINCT i.film_id)
            FROM rental r
            JOIN inventory i ON i.inventory_id = r.inventory_id
            JOIN payment p ON p.rental_id = r.rental_id
            WHERE r.customer_id = c.customer_id
        )::BIGINT AS unique_films,
        (
            SELECT COALESCE(AVG(f.rental_duration), 0)
            FROM rental r
            JOIN inventory i ON i.inventory_id = r.inventory_id
            JOIN film f ON f.film_id = i.film_id
            JOIN payment p ON p.rental_id = r.rental_id
            WHERE r.customer_id = c.customer_id
        )::DECIMAL AS avg_rental_duration
    FROM customer c
    JOIN address a ON a.address_id = c.address_id
    JOIN city ci ON ci.city_id = a.city_id
    JOIN country co ON co.country_id = ci.country_id
    LEFT JOIN paid_rentals pr ON pr.customer_id = c.customer_id
),
customer_categories AS (
    SELECT DISTINCT ON (r.customer_id)
        r.customer_id,
        cat.name AS favorite_category
    FROM (
        SELECT
            r.customer_id,
            fc.category_id,
            RANK() OVER (PARTITION BY r.customer_id ORDER BY COUNT(*) DESC) AS rk
        FROM rental r
        JOIN payment p ON p.rental_id = r.rental_id
        JOIN inventory i ON i.inventory_id = r.inventory_id
        JOIN film_category fc ON fc.film_id = i.film_id
        GROUP BY r.customer_id, fc.category_id
    ) r
    JOIN category cat ON cat.category_id = r.category_id
    WHERE r.rk = 1
),
customer_actors AS (
    SELECT DISTINCT ON (r.customer_id)
        r.customer_id,
        (a.first_name || ' ' || a.last_name) AS favorite_actor
    FROM (
        SELECT
            r.customer_id,
            fa.actor_id,
            RANK() OVER (PARTITION BY r.customer_id ORDER BY COUNT(*) DESC) AS rk
        FROM rental r
        JOIN payment p ON p.rental_id = r.rental_id
        JOIN inventory i ON i.inventory_id = r.inventory_id
        JOIN film_actor fa ON fa.film_id = i.film_id
        GROUP BY r.customer_id, fa.actor_id
    ) r
    JOIN actor a ON a.actor_id = r.actor_id
    WHERE r.rk = 1
),
regional_popular_films AS (
    SELECT
        co.country_id,
        f.title AS most_popular_film_in_region,
        COUNT(*)::BIGINT AS regional_film_rental_count
    FROM rental r
    JOIN payment p ON p.rental_id = r.rental_id
    JOIN inventory i ON i.inventory_id = r.inventory_id
    JOIN film f ON f.film_id = i.film_id
    JOIN customer c ON c.customer_id = r.customer_id
    JOIN address a ON a.address_id = c.address_id
    JOIN city ci ON ci.city_id = a.city_id
    JOIN country co ON co.country_id = ci.country_id
    GROUP BY co.country_id, f.film_id, f.title
),
regional_ranked AS (
    SELECT
        country_id,
        most_popular_film_in_region,
        regional_film_rental_count,
        ROW_NUMBER() OVER (PARTITION BY country_id ORDER BY regional_film_rental_count DESC) AS rn
    FROM regional_popular_films
),
regional_one AS (
    SELECT country_id, most_popular_film_in_region, regional_film_rental_count
    FROM regional_ranked
    WHERE rn = 1
)
SELECT
    cbs.customer_id,
    cbs.customer_name,
    cbs.city,
    cbs.country,
    COALESCE(cbs.total_rentals, 0)::BIGINT AS total_rentals,
    COALESCE(cbs.unique_films, 0)::BIGINT AS unique_films,
    COALESCE(cbs.total_spent, 0)::DECIMAL AS total_spent,
    cc.favorite_category,
    ca.favorite_actor,
    COALESCE(cbs.avg_rental_duration, 0)::DECIMAL AS avg_rental_duration,
    CASE
        WHEN COALESCE(cbs.total_spent, 0) >= 200 THEN 'Platinum'
        WHEN COALESCE(cbs.total_spent, 0) >= 150 THEN 'Gold'
        WHEN COALESCE(cbs.total_spent, 0) >= 100 THEN 'Silver'
        ELSE 'Bronze'
    END AS customer_tier,
    ro.most_popular_film_in_region,
    COALESCE(ro.regional_film_rental_count, 0)::BIGINT AS regional_film_rental_count
FROM customer_basic_stats cbs
LEFT JOIN customer_categories cc ON cc.customer_id = cbs.customer_id
LEFT JOIN customer_actors ca ON ca.customer_id = cbs.customer_id
LEFT JOIN regional_one ro ON ro.country_id = cbs.country_id
ORDER BY cbs.customer_id
"""


class CustomerAnalysisFixTask(PostgresTask):
    """Task: fix buggy customer analysis and create customer_analysis_fixed with full 13-column output."""

    name = "customer_analysis_fix"
    goal = """Fix the buggy customer analysis and create a correct results table in the DVD rental database.

## Your Task

A customer analysis query has bugs (e.g. wrong joins or aggregates). You must fix it and create a table **customer_analysis_fixed** with **all** of the following columns (one row per customer, 587 rows):

1. **customer_id** (integer)
2. **customer_name** (text) — first_name || ' ' || last_name from customer
3. **city** (text) — from address → city
4. **country** (text) — from address → city → country
5. **total_rentals** (bigint) — count of distinct rental_id in payment for that customer
6. **unique_films** (bigint) — count of distinct films rented (via rental → inventory → film, only paid rentals)
7. **total_spent** (numeric/decimal) — sum of payment.amount
8. **favorite_category** (text) — category with the most rentals for that customer (from film_category, category)
9. **favorite_actor** (text) — actor with the most films rented (from film_actor, actor; first_name || ' ' || last_name)
10. **avg_rental_duration** (numeric) — average film.rental_duration (in days) over films they rented (paid rentals only)
11. **customer_tier** (text) — 'Platinum' if total_spent >= 200, 'Gold' if >= 150, 'Silver' if >= 100, else 'Bronze'
12. **most_popular_film_in_region** (text) — film title with the most rentals in the customer's country (country from their address)
13. **regional_film_rental_count** (bigint) — rental count for that film in that country

Use tables: customer, address, city, country, payment, rental, inventory, film, film_category, category, film_actor, actor. Preserve decimal types for total_spent and avg_rental_duration. Order by customer_id for verification. The evaluator compares your table to a full ground-truth CTE with decimal tolerance (e.g. 0.1).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (
            SqlResultMatches(
                CUSTOMER_ANALYSIS_QUERY,
                expected_query=CUSTOMER_ANALYSIS_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
