"""
ETL pipeline - summarizes raw query_history rows into a daily_stats table,
so Tableau can show trends without scanning every row.

Extract  -> reads raw rows from request_log and error_log
Transform -> aggregates them by day
Load     -> writes the summary into daily_stats (creates the table if needed)

Works against either database, same pattern as app.py:
- If DATABASE_URL is set (e.g. in GitHub Actions, pointed at Neon) -> uses that

Run manually with:  python etl_daily_stats.py
Runs automatically once a day via GitHub Actions (see .github/workflows/etl.yml)
"""
import os
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()  # picks up .env when running locally; harmless if it doesn't exist (e.g. in CI)

# ==================== DATABASE CONNECTION (Neon) ====================
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to .env for local runs, "
        "or as a GitHub Actions secret."
    )

print("Connecting to: Neon (via DATABASE_URL)")
engine = create_engine(DATABASE_URL)
# ==================== END DATABASE CONNECTION ====================


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    stat_date DATE UNIQUE NOT NULL,
    total_queries INTEGER NOT NULL,
    generated_queries INTEGER NOT NULL,
    blocked_queries INTEGER NOT NULL,
    error_queries INTEGER NOT NULL,
    unique_users INTEGER NOT NULL,
    failure_rate NUMERIC(5,2) NOT NULL,
    run_at TIMESTAMP DEFAULT NOW()
);
"""

# Extract + Transform + Load in one statement
UPSERT_SQL = """
INSERT INTO daily_stats (
    stat_date, total_queries, generated_queries, blocked_queries,
    error_queries, unique_users, failure_rate
)
SELECT
    created_at::date,
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'generated'),
    COUNT(*) FILTER (WHERE status = 'blocked'),
    COUNT(*) FILTER (WHERE status = 'error'),
    COUNT(DISTINCT user_id),
    COALESCE(ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('blocked', 'error'))
                   / NULLIF(COUNT(*), 0), 2), 0)
FROM query_history
GROUP BY created_at::date
ON CONFLICT (stat_date) DO UPDATE SET
    total_queries = EXCLUDED.total_queries,
    generated_queries = EXCLUDED.generated_queries,
    blocked_queries = EXCLUDED.blocked_queries,
    error_queries = EXCLUDED.error_queries,
    unique_users = EXCLUDED.unique_users,
    failure_rate = EXCLUDED.failure_rate,
    run_at = NOW();
"""

def run_etl():
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        conn.execute(text(UPSERT_SQL))
        days = conn.execute(text("SELECT COUNT(*) FROM daily_stats")).scalar()
        print(f"ETL complete - {days} day(s) in daily_stats as of {date.today()}")


if __name__ == "__main__":
    run_etl()