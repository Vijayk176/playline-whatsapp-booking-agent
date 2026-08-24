# PlayLine — WhatsApp AI Booking Agent for Gaming Zones

A production-ready, white-label WhatsApp AI booking assistant for gaming lounges/zones. Customers message a gaming zone's WhatsApp Business number to check prices, check availability, book/cancel/reschedule gaming sessions, and get business info — all in English, Urdu, or Roman Urdu.

**This is a multi-client product, not a one-off build.** Every business-specific detail — name, address, hours, gaming options, prices, social links, AI greeting — lives in the database and is edited per-client through the `/admin/settings` and `/admin/games` pages. The codebase itself has no hardcoded business identity, so the same deployment (or a fresh clone) can be rebranded for a new gaming zone client in minutes, no code changes required.

## Architecture

```
Customer (WhatsApp)
      │
      ▼
Meta WhatsApp Cloud API
      │  webhook
      ▼
FastAPI  (/webhook)
      │
      ▼
Conversation Service ── stores messages, builds short history
      │
      ▼
AI Agent (Groq, tool-calling)  ──fallback──▶  Keyword Fallback Agent
      │  calls tools
      ▼
Tool Executor ──▶ Booking Service (pure Python, deterministic)
      │
      ▼
SQLite/PostgreSQL Database
```

**Key design decision:** the AI never touches the database directly and never does date math or availability logic itself. It only decides *which tool to call* and phrases the natural-language reply. All validation (business hours, overlaps, price calculation, booking IDs) is deterministic Python in `app/services/booking_service.py`. This keeps the system safe, testable, and cheap to run on free AI tiers.

## Features

- WhatsApp Cloud API webhook (GET verify + POST receive)
- AI agent (Groq/Llama 3.3 70B) with tool-calling: get prices, check availability, create/cancel/reschedule bookings, business info, human handoff
- Keyword-based fallback mode if the AI API fails or has no key configured
- Roman Urdu / Urdu / English understanding (AI mode) + basic Roman Urdu keywords (fallback mode)
- Deterministic overlap detection and business-hours validation
- Human handoff creates a support-desk ticket **and** instantly pages the venue owner/staff over WhatsApp (configurable number in Settings), so requests aren't only visible if someone happens to have the dashboard open
- Admin dashboard (Bootstrap 5): stats, bookings, gaming options, customers, support requests, settings
- JWT-cookie admin authentication, bcrypt password hashing
- SQLite for local dev, structured to swap in PostgreSQL for production
- Idempotent webhook processing (dedupes WhatsApp message IDs)
- Basic in-memory rate limiting
- Automated tests (pytest) for booking logic, overlaps, cancellation, rescheduling, webhook parsing

## Project Structure

```
odyssey-whatsapp-agent/
├── app/
│   ├── main.py              FastAPI app, route registration, startup
│   ├── config.py            Settings loaded from .env
│   ├── database.py          SQLAlchemy engine/session
│   ├── models/models.py     All ORM models
│   ├── schemas/schemas.py   Pydantic request/response schemas
│   ├── routes/              webhook, bookings, games, customers, support,
│   │                        settings, admin_auth, admin_pages
│   ├── services/            booking_service (core logic), whatsapp,
│   │                        auth_service, conversation_service
│   ├── agents/               tools.py (tool defs+executor), prompts.py,
│   │                        groq_agent.py, fallback_agent.py, base.py
│   ├── utils/                timezone, security, rate_limit
│   └── templates/           Jinja2 admin dashboard pages
├── static/                  CSS/JS for admin dashboard
├── tests/                   pytest suite
├── seed.py                  Seeds SAMPLE gaming options + business settings
├── run.py                   Local dev entrypoint
├── requirements.txt
├── .env.example
└── .gitignore
```

## 1. Local Setup (Windows / PowerShell)

```powershell
# 1. Create project folder & open in VS Code
mkdir odyssey-whatsapp-agent
cd odyssey-whatsapp-agent
code .

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and fill in GROQ_API_KEY, WHATSAPP_* values, ADMIN_PASSWORD, SECRET_KEY

# 5. Seed the database (creates SQLite file + sample data + admin user)
python seed.py

# 6. Run the server
python run.py
```

The app runs at `http://localhost:8000`.

- Swagger API docs: `http://localhost:8000/docs`
- Admin dashboard: `http://localhost:8000/admin/login` (default: `admin` / whatever you set as `ADMIN_PASSWORD`)
- Health check: `http://localhost:8000/health`

> **Note:** if you see a bcrypt/passlib error on first run, it's caused by a version mismatch between `passlib` and newer `bcrypt` releases. `requirements.txt` already pins `bcrypt==4.0.1` to avoid this — just make sure you installed from the provided `requirements.txt`.

## 2. Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Used to sign admin session JWTs. Change this. |
| `DATABASE_URL` | `sqlite:///./odyssey.db` locally; use a `postgresql://...` URL in production. |
| `AI_PROVIDER` | Currently `groq`. Falls back to keyword mode automatically if unset/fails. |
| `GROQ_API_KEY` | Get a free key at https://console.groq.com |
| `WHATSAPP_TOKEN` | Meta permanent/temporary access token |
| `WHATSAPP_PHONE_NUMBER_ID` | From Meta WhatsApp Business API setup |
| `WHATSAPP_VERIFY_TOKEN` | Any string you choose; must match what you enter in Meta's webhook setup |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | From Meta Business Manager |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Seeded as the first admin login |
| `TIMEZONE` | Defaults to `Asia/Karachi` |

**Owner notification number** is not set via `.env` — configure it per-client at `/admin/settings` → "Owner Notification Number". Whenever the AI escalates to a human (customer asks for staff, or is frustrated/stuck), that number gets an instant WhatsApp alert with the customer's number and the reason, in addition to the request appearing on `/admin/support`.

Never commit `.env` — it's already in `.gitignore`.

## 3. Testing

```powershell
pip install pytest
pytest tests/ -v
```

Covers: gaming options, price calculation, booking creation, overlap rejection, non-overlap acceptance, cancellation freeing a slot, rescheduling, business-hours validation, past-booking rejection, booking ID format, and webhook payload parsing.

## 4. Testing the API Manually

```powershell
# Health check
curl http://localhost:8000/health

# List gaming options
curl http://localhost:8000/api/games

# Create a booking
curl -X POST http://localhost:8000/api/bookings -H "Content-Type: application/json" -d "{\"customer_name\":\"Ali\",\"phone\":\"923001234567\",\"gaming_option_id\":1,\"booking_date\":\"2026-08-25\",\"start_time\":\"19:00:00\",\"duration_hours\":2}"
```

Or use the interactive Swagger UI at `/docs`.

## 5. WhatsApp Cloud API Setup

1. Create a Meta Developer app at https://developers.facebook.com and add the **WhatsApp** product.
2. Copy the temporary access token and phone number ID into `.env`.
3. Deploy the app somewhere with a public HTTPS URL (see Deployment below), or use `ngrok http 8000` for local testing.
4. In the Meta app's WhatsApp → Configuration screen, set the **Callback URL** to `https://your-domain/webhook` and the **Verify Token** to the same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`.
5. Subscribe to the `messages` webhook field.
6. Send a WhatsApp message to your test number — it should trigger `POST /webhook` and get a reply.

## 6. AI Configuration (Groq)

1. Sign up free at https://console.groq.com and create an API key.
2. Put it in `.env` as `GROQ_API_KEY`.
3. Restart the server. The agent automatically uses Groq's tool-calling; if the key is missing or a request fails, it transparently falls back to the keyword-based `FallbackAgent` so the bot never goes fully silent.

To add another AI provider later, implement `BaseAgent.respond()` in a new file under `app/agents/` and select it in `app/services/conversation_service.py::_get_agent()`.

## 7. Deployment

Recommended free/low-cost hosts: **Render**, **Railway**, or **Fly.io** (check current free-tier terms, as these change often).

General steps:
1. Push this repo to GitHub (see below).
2. Create a new Web Service on your chosen host, pointing at this repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all `.env` variables as environment variables/secrets in the host's dashboard — **do not** commit `.env`.
6. Switch `DATABASE_URL` to a managed PostgreSQL instance (most hosts offer a free/low-cost Postgres add-on). The code already uses SQLAlchemy so no code changes are needed — just update the URL and re-run `python seed.py` once against production if you want sample data (or seed manually via the admin dashboard).
7. Meta's WhatsApp Cloud API **requires HTTPS** for the webhook — all of the hosts above provide this by default.
8. Once deployed, repeat the "WhatsApp Cloud API Setup" steps above using your production HTTPS URL.

## 8. GitHub

```powershell
git init
git add .
git commit -m "Initial commit: PlayLine WhatsApp AI booking agent"
git branch -M main
git remote add origin https://github.com/<your-username>/odyssey-whatsapp-agent.git
git push -u origin main
```

`.gitignore` already excludes `.env`, database files, `__pycache__`, and virtual environments.

## 9. Security Notes

- Admin passwords are bcrypt-hashed, never stored in plaintext.
- Admin routes require a valid signed session cookie (JWT).
- All booking validation happens server-side; the AI cannot bypass business rules.
- Webhook GET requests are verified against `WHATSAPP_VERIFY_TOKEN`.
- Rate limiting middleware protects against basic API abuse.
- Never commit `.env` or API keys — the `.gitignore` already covers this.

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `bcrypt` error on startup | Make sure `bcrypt==4.0.1` is installed (already pinned in `requirements.txt`). |
| Webhook verification fails (403) | Check `WHATSAPP_VERIFY_TOKEN` in `.env` matches exactly what you entered in Meta's dashboard. |
| AI replies feel generic/wrong | Check `GROQ_API_KEY` is set and valid; check `server.log`/console for "Failed to initialize Groq agent" — it silently falls back to keyword mode if the key is missing. |
| Booking always "unavailable" | Check `business_settings.opening_time` / `closing_time` in the admin Settings page — times outside this range are rejected. |
| Duplicate WhatsApp replies | Confirm your webhook isn't registered twice in Meta; the app already dedupes by WhatsApp message ID. |

---

## FINAL PROJECT CHECKLIST

- [x] Python environment working
- [x] Database working (SQLite, SQLAlchemy models)
- [x] Admin login working (bcrypt + JWT cookie)
- [x] Gaming options working (CRUD via admin + API)
- [x] Booking creation working
- [x] Availability checking working (overlap detection + nearby-time suggestions)
- [x] Cancellation working
- [x] Rescheduling working
- [x] AI working (Groq tool-calling agent)
- [x] Fallback working (keyword-based agent when AI unavailable)
- [x] WhatsApp webhook working (verify + receive, tested with sample payloads)
- [ ] WhatsApp messages working end-to-end (requires your real Meta credentials — not testable without them)
- [x] Admin dashboard working (all 6 pages render and function)
- [x] Tests passing (13/13)
- [ ] GitHub configured (run the commands in section 8)
- [ ] Deployment ready (follow section 7 once you choose a host)

## WHAT TO CHANGE FOR EACH NEW GAMING ZONE CLIENT

Everything below is currently a clearly-labeled **SAMPLE** value. Replace via the `/admin/settings` and `/admin/games` pages — no code changes needed per client:

- Business name and real address
- Real phone number
- Real WhatsApp Business number
- `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_BUSINESS_ACCOUNT_ID` (unique per client, from that client's Meta app)
- Actual gaming options offered (names may differ from the sample PS5/PS4/PC/Xbox/Racing Simulator list)
- Actual prices per hour for each gaming option
- Real opening/closing hours and weekly closed day (if any)
- Real Google Maps link
- Real Instagram/Facebook links
- `GROQ_API_KEY` (can be shared across clients, or one per client for cost tracking)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` (unique per client deployment; change from defaults before going live)

**Multi-client note:** the simplest path to running this for multiple gaming zones is one deployment (app + database) per client, each with its own `.env` and its own WhatsApp number/token. The code is identical across all of them — only the `.env` and the data entered via the admin dashboard differ.
