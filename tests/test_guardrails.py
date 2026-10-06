from guardrails import validate_and_prepare, NEVER_EXPOSE, MAX_ROWS


def test_allows_a_plausible_generated_query():
    sql, reason, status = validate_and_prepare(
        "SELECT employee_name, salary FROM employees ORDER BY salary DESC LIMIT 5"
    )
    assert status == "generated"
    assert reason is None
    assert sql is not None
    assert "LIMIT" in sql.upper()


def test_works_for_any_domain_not_just_one_schema():
    for sql_text in [
        "SELECT title, author FROM books WHERE published_year > 2020",
        "SELECT name, population FROM cities ORDER BY population DESC",
        "SELECT p.name, c.name FROM planets p JOIN constellations c ON p.constellation_id = c.id",
    ]:
        sql, reason, status = validate_and_prepare(sql_text)
        assert status == "generated", f"expected generated for: {sql_text}"


def test_blocks_drop_table():
    sql, reason, status = validate_and_prepare("DROP TABLE employees")
    assert status == "blocked"
    assert sql is None
    assert reason is not None


def test_blocks_delete():
    sql, reason, status = validate_and_prepare("DELETE FROM employees WHERE id = 1")
    assert status == "blocked"
    assert sql is None


def test_blocks_update():
    sql, reason, status = validate_and_prepare("UPDATE employees SET salary = 999999")
    assert status == "blocked"


def test_blocks_stacked_statements():
    sql, reason, status = validate_and_prepare(
        "SELECT * FROM employees; DROP TABLE employees;"
    )
    assert status == "blocked"
    assert sql is None


def test_blocks_protected_internal_table():
    sql, reason, status = validate_and_prepare('SELECT * FROM "user"')
    assert status == "blocked"
    assert sql is None
    assert "protected" in reason.lower()


def test_blocks_query_history_table_too():
    sql, reason, status = validate_and_prepare("SELECT * FROM query_history")
    assert status == "blocked"


def test_cte_name_is_not_treated_as_a_protected_table():
    sql, reason, status = validate_and_prepare(
        "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent"
    )
    assert status == "generated"


def test_cte_cannot_be_used_to_smuggle_a_protected_table():
    sql, reason, status = validate_and_prepare(
        'WITH t AS (SELECT * FROM "user") SELECT * FROM t'
    )
    assert status == "blocked"
    assert "protected" in reason.lower()


def test_forces_row_limit():
    sql, reason, status = validate_and_prepare("SELECT * FROM employees LIMIT 999999")
    assert status == "generated"
    assert sql is not None
    assert str(MAX_ROWS) in sql


def test_blocks_disallowed_function():
    sql, reason, status = validate_and_prepare("SELECT pg_sleep(10)")
    assert status == "blocked"


def test_never_expose_set():
    assert NEVER_EXPOSE == {"user", "query_history"}