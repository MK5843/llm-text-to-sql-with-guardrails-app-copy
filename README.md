# Text-to-PostgreSQL with Guardrails

Type a question in plain English. Get a PostgreSQL query back.

For example, you type *"Who are the 5 highest paid employees?"* and the app gives you the SQL code that would answer it.

> **Important:** this app only *writes* the SQL. It never runs it. Your data is never touched.

## **Try it live:** [https://llm-text-to-sql-with-guardrails-app.onrender.com/]
## **Full guide:** open `user_guide_documentation-copy.html` in your browser

<!-- Add a screenshot of the app here -->

---

## What is this?

SQL is the language used to ask questions to a database. Many people don't know how to write it. This app does the writing for you.

It also checks every query before showing it, so nothing unsafe gets through. These checks are called **guardrails**.

## What can it do?

- Turn your question into SQL, on any topic
- Use an AI model on your own computer, and switch to another AI (OpenAI, Claude or Gemini) if the first one is not working
- Check every query for safety before showing it
- Let people sign up with an email and password, or with their Google account
- Save each person's past questions in a history list that only they can see
- Build a daily summary of how the app is used
- Show that summary in a Tableau dashboard
- Work on phones, tablets and computers

## How do the safety checks work?

Every query the AI writes goes through these checks:

| Check | What it does |
|---|---|
| Is it real SQL? | If the code is broken, it is blocked |
| Is it only a question? | Only `SELECT` queries are allowed. Anything that changes or deletes data (like `DROP` or `DELETE`) is blocked |
| Is it one query? | Two queries stuck together are blocked |
| Does it touch private tables? | Queries that try to read the app's own user and history tables are blocked |
| Does it use risky tools? | A short list of dangerous functions is blocked |
| Is it too big? | The number of rows is limited to 200 |

Every question ends with one of three results:

- **generated:** the query is safe and ready to read
- **blocked:** the query broke a rule. You are shown the query and the reason
- **error:** something went wrong, for example all the AI services were down

## What is it made with?

| Part | Tool |
|---|---|
| Website and server | Python and Flask |
| Checking the SQL | sqlglot |
| AI | LM Studio (Qwen), OpenAI, Claude, Gemini |
| Database | PostgreSQL on Neon (free) |
| Hosting the live site | Render |
| Daily automatic jobs | GitHub Actions |
| Charts and dashboard | Tableau |
| Tests | pytest |

## What is in each file?

```
app.py                  The main app: pages, login, and the "ask a question" part
extensions.py           Small helpers the app shares
models.py               How users and history are saved in the database
llm.py                  Talks to the AI models
guardrails.py           The safety checks
etl_daily_stats.py      Makes the daily summary
conftest.py             Helps the tests find the code
templates/              The web pages (login and main page)
static/                 The look of the pages (style and scripts)
tests/                  Automatic tests
tableau dashboard/      The Tableau file
.github/workflows/      The daily automatic job
.env.example            A list of settings you need to fill in
user_guide_documentation.html   The full step-by-step guide
```

## How to run it on your computer

### What you need first

- Python 3.12 or newer
- Git
- A free [Neon](https://neon.tech) database
- Optional: [LM Studio](https://lmstudio.ai) for a free AI on your own computer, or a key for OpenAI, Claude or Gemini

### Step 1: Get the code

```bash
git clone https://github.com/MK5843/llm-text-to-sql-with-guardrails-app-copy.git
cd llm-text-to-sql-with-guardrails-app-copy
```

### Step 2: Make a private space for the packages

```bash
python -m venv venv
source venv/Scripts/activate
```

On Mac or Linux, use `source venv/bin/activate` instead.
When it works, you will see `(venv)` at the start of the line.

### Step 3: Install the packages

```bash
pip install -r requirements.txt
```

### Step 4: Fill in your settings

Copy the example settings file:

```bash
cp .env.example .env
```

Open `.env` and fill it in. Here is what each setting means:

| Setting | What it is |
|---|---|
| `SECRET_KEY` | A random secret for keeping logins safe |
| `ENCRYPTION_KEY` | A secret key used to scramble saved questions |
| `DATABASE_URL` | The link to your Neon database |
| `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` | Needed for "Sign in with Google" |
| `LLM_PROVIDER` | Which AI to try first (`lmstudio`, `openai`, `claude` or `gemini`) |
| `LLM_FALLBACK_ORDER` | Which AI to try next if the first one fails |
| `LLM_BASE_URL` and `LLM_MODEL` | The address and name of your LM Studio model |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` | Passwords for each AI service (only add the ones you use) |

To make an `ENCRYPTION_KEY`, run this and copy what it prints:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Be careful:**
- Never upload your `.env` file to GitHub. It holds your secrets.
- Keep a safe copy of `ENCRYPTION_KEY`. If you lose it, saved questions can never be read again.

### Step 5: Start the app

```bash
python app.py
```

Open the address it shows, usually `http://127.0.0.1:5000`, in your browser.

Tip: Google treats `127.0.0.1` and `localhost` as two different places. Use the same one in your browser and in your Google settings.

## How to run the tests

```bash
pip install pytest
pytest tests/ -v
```

The tests check that the safety rules block the bad queries and allow the good ones.

## The daily summary

Once a day, a small program (`etl_daily_stats.py`) counts how many questions were asked, how many were safe, blocked or failed, and how many people used the app. It saves the counts in a table called `daily_stats`.

It only counts. It never copies anyone's questions or SQL, so private text stays private.

GitHub runs it for you every day at 03:00 UTC. You can also run it by hand from the **Actions** tab on GitHub.

For this to work, add a secret on GitHub called `DATABASE_URL`:
**Settings → Secrets and variables → Actions → New repository secret**

Then connect Tableau to the `daily_stats` table to see the charts.

## How to put it on the internet (Render)

1. Make a free account on [Render](https://render.com)
2. Create a new **Web Service** and connect this GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app --timeout 90`
5. Add all your settings from `.env` in Render's **Environment** page
6. Set `LLM_PROVIDER` to OpenAI, Claude or Gemini. Render cannot reach LM Studio on your own computer
7. Add your live website link to your Google sign-in settings

Your computer and the live site use the same Neon database.

## Staying safe

- Passwords are turned into a code that cannot be changed back, so nobody can read them
- Saved questions and SQL are scrambled so they look like random letters in the database
- Safety checks run on every query
- Nothing the AI writes is ever run
- Secrets stay in settings files and are never put in the code

## Words you might not know

| Word | Meaning |
|---|---|
| SQL | The language used to ask a database for information |
| PostgreSQL | A popular type of database |
| Guardrails | Safety checks that stop bad queries |
| Database | A place where information is stored in tables |
| API key | A private password that lets the app use a service |
| Encrypted | Scrambled so only someone with the key can read it |
| Deploy | Put the app on the internet so anyone can open it |