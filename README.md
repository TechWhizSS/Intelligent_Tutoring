# Syllabus to Song

A full-stack, mobile-friendly educational music studio for **MBA Tech → CE → First year → Semester I**, covering Calculus and Basic Electrical & Electronics Engineering.

**Demonstrable now:** sample SAP login, all 91 uploaded topic headings, source-linked summaries and formulas, supplemental Hindi explanations, English/Hindi lyric templates, editable/saved drafts, quizzes, SQLite song library, admin source uploads and approval, a browser audio player with seeking and downloads, and a complete syllabus readiness report.

**Live sung music is blocked in the supplied environment:** no `GEMINI_API_KEY` is configured, and the Google API host is absent from the environment allowlist. The official Gemini/Lyria adapter is implemented and contract-tested with mocks, but no live provider generation has been verified. Demo mode does not invent audio, use TTS, or substitute commercial song recordings. Full textbook notes were not uploaded; the app labels uploaded summaries and supplemental guidance separately.

## Launch

Python **3.12+** is the only runtime requirement. No npm build, pip install, database server, or laptop-specific setup is needed.

```sh
git clone https://github.com/TechWhizSS/Intelligent_Tutoring.git
cd Intelligent_Tutoring
git switch codex/development
python3 -m app.server
```

Open **http://localhost:8000**. On a cloud host, expose/forward port 8000 through that host's authenticated preview. The local server address is not a public deployment URL.

- Student: any SAP ID with 3–30 letters/digits/underscores/hyphens and **any nonempty password**.
- “Try the sample student account” opens `70572400001` and seeds Calculus/BEEE lyric examples in both languages, with **no audio**.
- Demo admin: SAP ID `admin`, password `demo-admin`. Set `ADMIN_PASSWORD` before sharing an instance.
- Only English (`en`) and Hindi (`hi`) are accepted by the API and database language constraint.
- Runtime files are stored in `runtime/` and excluded from Git. For a persistent host volume, set `APP_DATA_DIR` to that volume.

## Turn on real sung music

Configure the environment's secret binding `GEMINI_API_KEY` with an API key authorized for Gemini and Lyria 3.5. Enable required billing/model permissions and outbound HTTPS to **generativelanguage.googleapis.com**. Restart the server after changing environment variables. Keep the key out of chat, source control, and browser code.

For a shell-configured instance:

```sh
cp .env.example .env
# Edit .env securely with the real key and admin password.
set -a
. ./.env
set +a
python3 scripts/check_providers.py
python3 -m app.server
```

The credential check calls model metadata endpoints; it does **not** buy an audio generation and does **not** certify generation. In the UI choose **Live Gemini**, generate and review lyrics, then click **Synthesize sung music**. Synthesis runs in the background; completed provider audio appears in the player and library. Exact tempo, voice, genre, length and repeated-formula adherence are prompt preferences, not guaranteed API controls. Live errors remain explicit; no silent demo fallback occurs.

The server uses official REST `models/{model}:generateContent` calls. Defaults: `gemini-3.8-flash` and `lyria-3.5`; model names are configurable. See [provider documentation and validation evidence](docs/PROVIDERS.md).

## Submission walkthrough

1. Start the server and click **Try the sample student account**.
2. Choose Calculus → Unit 1 → Rolle's Theorem → English. Generate an offline template, edit a line, and save.
3. Repeat for BEEE → Unit 1 → Electrical Circuit Elements, then switch to Hindi. Notes include supplemental worked examples for both topics.
4. Take a quiz and view feedback. Open the library to revisit saved drafts.
5. Open **Syllabus report** to inspect all 91 topics and download the CSV. Indexed coverage, full-note readiness, draft readiness and audio readiness are distinct.
6. With configured provider access, select live generation and synthesize. Without it, demonstrate the honest blocker. If you have an educational recording you may use, attach a WAV/MP3; it is explicitly labelled **user supplied**, not AI generated. The player supports play/pause, seeking, volume and download.
7. Sign in as the demo admin. Upload a source file and academic excerpt, review it, then approve it. Only approved excerpts enter Gemini grounding. Uploaded files never modify the official hierarchy or act as instructions.

Repeatable command-line examples against a running server:

```sh
python3 scripts/demo.py
python3 scripts/demo.py --language hi
# These make billable provider calls only after credentials are configured:
python3 scripts/demo.py --live
python3 scripts/demo.py --live --language hi
```

The script runs one Calculus and one BEEE example and saves outputs under `runtime/demo-output/`. Sign in as `submission-demo` with any password to view them. Live runs download only real audio returned by Lyria. The present environment has completed offline flows; live sung end-to-end examples remain blocked.

## Validate

```sh
python3 -m compileall -q app scripts tests
node --check static/app.js
python3 -m unittest discover -s tests -v
```

Node is optional for a JavaScript syntax check, not required to run the app. Backend tests use the Python standard library and a temporary database. For browser checks:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 tests/browser_smoke.py
```

The browser suite creates an isolated temporary server. It verifies both subjects in both languages, editing/saving, the provider blocker, quizzes, all report rows, uploads/approval, CSV/audio downloads, browser playback, playback continuity during navigation, and mobile/tablet layout. Its silent WAV is a **test-only player fixture**, never an educational demo song. Screenshots go to `test-results/` (Git-ignored). GitHub Actions runs checks on the development branch and pull requests to `main`.

## Sources and completeness

The original uploaded spreadsheet, PDF, CSV mappings, DOCX and nested ZIP files are preserved under `sources/`. The catalogue includes file hashes and exact source locations. The BEEE PDF preserves all lecture/lab scope and learning objectives; the app also links each topic to its uploaded lecture mapping. Calculus objectives are not invented where the workbook supplies none. Uploaded popular-song associations are reference metadata only; no recordings or copyrighted lyric rewrites are supplied.

See the [91-topic completeness report](docs/SYLLABUS_COMPLETENESS.md) and [complete CSV](docs/syllabus-completeness.csv). “100% indexed” means every uploaded topic is represented, not that complete textbook notes or generated music exist. The source contains mathematical simplifications; the app keeps the original and separately supplies cautions, including the domain condition for scalar potentials.

To rebuild the catalogue/report after an intentional source update:

```sh
python3 -m pip install openpyxl==3.1.5
python3 scripts/import_syllabus.py
python3 scripts/build_report.py
```

## Architecture and scope

- `app/server.py`: HTTP API, sessions, uploads, byte-range audio delivery, background synthesis.
- `app/store.py`: SQLite sessions, songs, quiz attempts and approved material.
- `app/providers.py`: server-only Google requests, grounded lyrics, actual audio parsing and explicit provider failures.
- `app/content.py`, `data/`: imported hierarchy, supplemental explanations, quizzes and labelled templates.
- `static/`: responsive browser UI; no frontend dependencies or external CDN requirement.
- `tests/`: API/provider/catalogue tests and isolated browser verification.

This is a single-process college-demo server. Sample student passwords intentionally do not verify a college identity. Do not use it for real student records or expose a billed key behind unrestricted sample login. Background jobs are marked failed after a server restart; retry them from the library. Use a durable data volume for songs/uploads and HTTPS with `COOKIE_SECURE=1` for a shared hosted instance. A public hosting deployment has not been created.

Development stays on `codex/development`. `main` must only receive changes through an approved merge.
