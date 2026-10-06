import sqlglot
from sqlglot import exp

# Tables this tool will never generate example SQL for, no matter how the
# question is phrased. These are this app's own internal tables (accounts,
# request history) - not tables it queries, since it never queries anything.
NEVER_EXPOSE = {"user", "query_history"}

MAX_ROWS = 200
FORBIDDEN_FUNCTIONS = {"pg_sleep", "pg_read_file", "dblink", "lo_import", "lo_export"}


def validate_and_prepare(sql: str) -> tuple[str | None, str | None, str]:
    """
    Checks AI-generated SQL before it's ever shown to the user. This tool
    never executes anything - every question just gets a checked SQL answer
    back. Returns (prepared_sql, reason, status), where status is:

      "generated" - passed every safety check, safe to display.
      "blocked"   - failed a safety check. prepared_sql is None.
    """
    if not sql or not sql.strip():
        return None, "Empty SQL generated.", "blocked"

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        return None, f"Could not parse SQL: {e}", "blocked"

    if not isinstance(parsed, exp.Select):
        return None, "Only SELECT statements are allowed.", "blocked"

    # Names defined by WITH ... AS (...) show up as table references but
    # aren't real tables, so leave them out of the checks below.
    cte_names = {cte.alias.lower() for cte in parsed.find_all(exp.CTE)}
    tables = {t.name.lower() for t in parsed.find_all(exp.Table)} - cte_names

    if tables & NEVER_EXPOSE:
        return None, f"Query touches a protected table: {sorted(tables & NEVER_EXPOSE)}", "blocked"

    used_funcs = {f.name.lower() for f in parsed.find_all(exp.Anonymous)}
    blocked_funcs = used_funcs & FORBIDDEN_FUNCTIONS
    if blocked_funcs:
        return None, f"Query uses a disallowed function: {sorted(blocked_funcs)}", "blocked"

    # Only cap a LIMIT the model already added if it's unreasonably large -
    # never add one that wasn't there. A query with no LIMIT (e.g. "total
    # revenue this year", an aggregate with one row) or with a reasonable
    # one stays exactly as generated.
    existing_limit = parsed.args.get("limit")
    if existing_limit is not None:
        try:
            current = int(existing_limit.expression.this)
            if current > MAX_ROWS:
                parsed.set("limit", exp.Limit(expression=exp.Literal.number(MAX_ROWS)))
        except (TypeError, ValueError, AttributeError):
            parsed.set("limit", exp.Limit(expression=exp.Literal.number(MAX_ROWS)))

    return parsed.sql(dialect="postgres"), None, "generated"