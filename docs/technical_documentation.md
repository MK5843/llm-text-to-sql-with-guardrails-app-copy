# Text-to-PostgreSQL with Guardrails: Technical Documentation

A short guide to how the app is built, in simple words.

## What the app does

You type a question in plain English. The app writes a PostgreSQL query for you. It checks the query for safety first, then shows it to you. **The app never runs the query**, so your data is never touched.

## How it works

1. You type a question and click **Generate SQL**.
2. The app asks an AI to write the SQL. If one AI is down, it tries the next one.
3. The safety checks look at the SQL.
4. The app saves your question and the result.
5. You see the SQL on the screen, with a status.

The status is one of three words:

| Status | What it means |
| --- | --- |
| generated | The query is safe |
| blocked | The query broke a safety rule. You see the reason |
| error | Something broke, for example every AI was down |

## The files

| File | What it does |
| --- | --- |
| `app.py` | The main app: pages, login, and the question part |
| `llm.py` | Talks to the AI |
| `guardrails.py` | The safety checks |
| `models.py` | How users and history are saved |
| `extensions.py` | Small helpers used by the other files |
| `etl_daily_stats.py` | Makes the daily summary |
| `templates/` and `static/` | The web pages and how they look |
| `tests/` | Automatic tests |

## The safety checks

Every query must pass these checks:

- It must be real SQL.
- It must be one `SELECT` query only. Anything that changes or deletes data is blocked.
- It must not use the app's own `user` or `query_history` tables.
- It must not use risky functions, such as `pg_sleep`.
- It can show at most 200 rows. A bigger limit is lowered to 200.

## The database

The app uses PostgreSQL on Neon. It has three tables.

| Table | What it holds |
| --- | --- |
| `user` | Email, password (saved as a code that cannot be turned back), Google ID, date created |
| `query_history` | Who asked, the question, the SQL, the status, a note, and the date. The question and SQL are scrambled (encrypted) when encryption is on |
| `daily_stats` | One row per day with counts: total, generated, blocked, error, users, and failure rate. It has no question text |

## The daily summary

Once a day, at 03:00 UTC, GitHub runs `etl_daily_stats.py`. It counts the day's questions and saves the counts in `daily_stats`. It only counts. It never copies question text. Tableau reads this table to draw the dashboard.

For this to work, your GitHub repo needs a secret called `DATABASE_URL`.

## Settings

Keep these in a `.env` file on your computer, and in Render's settings online. Never put them in the code.

| Setting | What it is |
| --- | --- |
| `SECRET_KEY` | Keeps logins safe |
| `ENCRYPTION_KEY` | Scrambles saved questions |
| `DATABASE_URL` | The link to the database |
| `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` | For Sign in with Google |
| `LLM_PROVIDER` and `LLM_FALLBACK_ORDER` | Which AI to try first, and which to try next |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` | Passwords for the AI services |

## Run it and test it

```bash
pip install -r requirements.txt
python app.py
pytest tests/ -v
```

The first line installs what the app needs. The second starts the app. The third runs the tests.

## Put it online

Render runs the live app. Use `pip install -r requirements.txt` as the build command and `gunicorn app:app --timeout 90` as the start command. Add all your settings on Render's Environment page.

## Good to know

- The app writes SQL but does not run it, so it cannot tell if the answer is right.
- The safety checks look for danger, not for mistakes.
- If you lose `ENCRYPTION_KEY`, scrambled questions can never be read again.
- Your computer and the live site use the same database.
