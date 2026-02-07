"""Fix buggy customer analysis query and create customer_analysis_fixed table in dvdrental."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Full 13-column output (mcpmark parity): customer_id, customer_name, customer_city, customer_country,
# total_rentals, unique_films, total_spent, favorite_category, favorite_actor,
# avg_rental_duration, customer_tier, most_popular_film_in_region, regional_film_rental_count
CUSTOMER_ANALYSIS_QUERY = """
SELECT customer_id, customer_name, customer_city, customer_country, total_rentals, unique_films,
       total_spent, favorite_category, favorite_actor, avg_rental_duration,
       customer_tier, most_popular_film_in_region, regional_film_rental_count
FROM customer_analysis_fixed
ORDER BY total_spent DESC, total_rentals DESC, customer_name ASC
"""

# Ground truth: exact mcpmark verify.py logic (paid_rentals row-based, HAVING >= 15, Premium/Standard/Basic, actual avg duration)
CUSTOMER_ANALYSIS_EXPECTED = """
WITH paid_rentals AS (
    SELECT DISTINCT
        r.rental_id,
        r.customer_id,
        r.inventory_id,
        r.rental_date,
        r.return_date
    FROM rental r
    JOIN payment p ON p.rental_id = r.rental_id
),
payments_by_customer AS (
    SELECT pr.customer_id, SUM(p.amount) AS total_spent
    FROM paid_rentals pr
    JOIN payment p ON p.rental_id = pr.rental_id
    GROUP BY pr.customer_id
),
customer_basic_stats AS (
    SELECT
        c.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        ci.city AS customer_city,
        co.country AS customer_country,
        COUNT(DISTINCT pr.rental_id) AS total_rentals,
        COUNT(DISTINCT i.film_id) AS unique_films,
        pbc.total_spent,
        AVG(EXTRACT(EPOCH FROM (pr.return_date - pr.rental_date)) / 86400.0) AS avg_rental_duration
    FROM customer c
    JOIN address a ON c.address_id = a.address_id
    JOIN city ci ON a.city_id = ci.city_id
    JOIN country co ON ci.country_id = co.country_id
    JOIN paid_rentals pr ON pr.customer_id = c.customer_id
    JOIN inventory i ON pr.inventory_id = i.inventory_id
    JOIN payments_by_customer pbc ON pbc.customer_id = c.customer_id
    WHERE c.email IS NOT NULL
    GROUP BY c.customer_id, c.first_name, c.last_name, ci.city, co.country, pbc.total_spent
    HAVING COUNT(DISTINCT pr.rental_id) >= 15
),
customer_categories AS (
    SELECT
        pr.customer_id,
        cat.name AS category_name,
        COUNT(*) AS category_count,
        ROW_NUMBER() OVER (
            PARTITION BY pr.customer_id
            ORDER BY COUNT(*) DESC, cat.name ASC
        ) AS rn
    FROM paid_rentals pr
    JOIN inventory i ON pr.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
    JOIN film_category fc ON f.film_id = fc.film_id
    JOIN category cat ON fc.category_id = cat.category_id
    JOIN customer c ON pr.customer_id = c.customer_id
    WHERE c.email IS NOT NULL
    GROUP BY pr.customer_id, cat.name
),
customer_actors AS (
    SELECT
        pr.customer_id,
        (a.first_name || ' ' || a.last_name) AS actor_name,
        COUNT(*) AS actor_count,
        ROW_NUMBER() OVER (
            PARTITION BY pr.customer_id
            ORDER BY COUNT(*) DESC, (a.first_name || ' ' || a.last_name) ASC
        ) AS rn
    FROM paid_rentals pr
    JOIN inventory i ON pr.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
    JOIN film_actor fa ON f.film_id = fa.film_id
    JOIN actor a ON fa.actor_id = a.actor_id
    JOIN customer c ON pr.customer_id = c.customer_id
    WHERE c.email IS NOT NULL
    GROUP BY pr.customer_id, a.first_name, a.last_name
),
regional_popular_films AS (
    SELECT
        co.country,
        f.title,
        COUNT(DISTINCT pr.rental_id) AS rental_count,
        ROW_NUMBER() OVER (
            PARTITION BY co.country
            ORDER BY COUNT(DISTINCT pr.rental_id) DESC, f.title ASC
        ) AS rn
    FROM paid_rentals pr
    JOIN customer c ON pr.customer_id = c.customer_id
    JOIN address a ON c.address_id = a.address_id
    JOIN city ci ON a.city_id = ci.city_id
    JOIN country co ON ci.country_id = co.country_id
    JOIN inventory i ON pr.inventory_id = i.inventory_id
    JOIN film f ON i.film_id = f.film_id
    WHERE c.email IS NOT NULL
    GROUP BY co.country, f.title
)
SELECT
    cbs.customer_id,
    cbs.customer_name,
    cbs.customer_city,
    cbs.customer_country,
    cbs.total_rentals,
    cbs.unique_films,
    cbs.total_spent,
    cc.category_name AS favorite_category,
    ca.actor_name AS favorite_actor,
    cbs.avg_rental_duration,
    CASE
        WHEN cbs.total_spent >= 150 THEN 'Premium'
        WHEN cbs.total_spent >= 75 THEN 'Standard'
        ELSE 'Basic'
    END AS customer_tier,
    rpf.title AS most_popular_film_in_region,
    rpf.rental_count AS regional_film_rental_count
FROM customer_basic_stats cbs
LEFT JOIN customer_categories cc ON cbs.customer_id = cc.customer_id AND cc.rn = 1
LEFT JOIN customer_actors ca ON cbs.customer_id = ca.customer_id AND ca.rn = 1
LEFT JOIN regional_popular_films rpf ON cbs.customer_country = rpf.country AND rpf.rn = 1
ORDER BY cbs.total_spent DESC, cbs.total_rentals DESC, cbs.customer_name ASC
"""


class CustomerAnalysisFixTask(PostgresTask):
    """Task: fix buggy customer analysis and create customer_analysis_fixed with full 13-column output."""

    name = "customer_analysis_fix"
    goal = """Fix the buggy customer analysis and create a correct results table in the DVD rental database.

## Your Task

A customer analysis query has bugs (e.g. wrong joins or aggregates). You must fix it and create a table **customer_analysis_fixed** with **all** of the following columns. Include **only customers with at least 15 paid rentals** (one row per such customer; exactly **587 rows**):

1. **customer_id** (integer)
2. **customer_name** (text) — first_name || ' ' || last_name from customer
3. **customer_city** (text) — from address → city
4. **customer_country** (text) — from address → city → country
5. **total_rentals** (bigint) — count of distinct rental_id in payment for that customer (paid rentals only)
6. **unique_films** (bigint) — count of distinct films rented (via rental → inventory → film, only paid rentals)
7. **total_spent** (numeric/decimal) — sum of payment.amount
8. **favorite_category** (text) — category with the most rentals for that customer (from film_category, category; paid rentals only)
9. **favorite_actor** (text) — actor with the most films rented (from film_actor, actor; first_name || ' ' || last_name; paid rentals only)
10. **avg_rental_duration** (numeric) — average of actual rental length in days over paid rentals: AVG(EXTRACT(EPOCH FROM (return_date - rental_date)) / 86400.0)
11. **customer_tier** (text) — 'Premium' if total_spent >= 150, 'Standard' if >= 75, else 'Basic'
12. **most_popular_film_in_region** (text) — film title with the most rentals in the customer's country (country from their address)
13. **regional_film_rental_count** (bigint) — rental count for that film in that country

Use tables: customer, address, city, country, payment, rental, inventory, film, film_category, category, film_actor, actor. Preserve decimal types for total_spent and avg_rental_duration. The evaluator compares your table to a full ground-truth CTE row-by-row with decimal tolerance (e.g. 0.1).
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
