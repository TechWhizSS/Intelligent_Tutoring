# Syllabus to Song — Gemini music handoff

**Current hosted section 2:** **Generate with Lyria** prepares the selected chapter/language/settings and any edited lyrics, copies the prompt and opens Gemini in the same tab on mobile or desktop. In Gemini, select **Create music**, paste and send. No supported native Gemini URL-prefill contract was found; the app does not claim that the prompt is already pasted or that music mode is automatically selected. Clipboard denial reveals selectable prompt text and a direct link instead of losing the prompt. Actual audio is created/played in Gemini; permitted downloads can be attached to the chapter. Gemini is the only music-generation option in the interface; no provider key form is shown.

A full-stack educational music studio for **MBA Tech → CE → First year → Semester I**, with all 38 uploaded Calculus topics and 53 uploaded BEEE topics indexed in order. Only English and Hindi are supported.

The current interface uses the Gemini website handoff only. No music API key is required. Your Gemini account controls eligibility and free music allowances. The retained ACE-Step local/GPU backend is legacy developer functionality, not an option in the current UI.

**Verification boundary:** no actual generated educational song or singing quality has been verified here. Clipboard/navigation and audio attachment/player tests do not prove Gemini music generation. See [provider evidence](docs/PROVIDERS.md).

## Open on your phone

[Open Syllabus to Song](https://syllabus-to-song-studio.aptcat4096.chatgpt.site) in Chrome or Safari. If prompted, sign in with the ChatGPT account that owns this private site, then use the sample student login. The interface adapts to phones and tablets; no laptop or localhost link is needed.

The studio uses a dark navigation rail, sage chapter banner, a dedicated Gemini prompt card, phone-sized input text and a persistent audio player. Chapter/music shortcuts move directly to the relevant controls.

## Run the website

Python 3.12+ is the only requirement for the website, catalogue, SQLite library, quizzes and uploads:

```sh
git clone https://github.com/TechWhizSS/Intelligent_Tutoring.git
cd Intelligent_Tutoring
git switch codex/development
python3 -m app.server
```

Open localhost:8000 or your cloud host's authenticated preview for port 8000. A separate Sites-hosted edition is provided for opening in Chrome; its Worker backend uses persistent R2 storage and the official free GPU API. The local Python backend and SQLite implementation remain intact. See `hosting/README.md` for deployment details.

- Student: any SAP ID containing 3–30 letters/digits/underscores/hyphens and any nonempty sample password.
- Sample account: click **Try the sample student account**. It includes Calculus and BEEE drafts in English and Hindi, without fake audio.
- Demo admin: `admin` / `demo-admin`; change `ADMIN_PASSWORD` before sharing.
- Runtime database, model files and generated audio are in Git-ignored `runtime/`. Set `APP_DATA_DIR` for a persistent host volume.

## Legacy GPU backend (developer reference)

The uploaded `design-experience-main.zip` contains an Android singing client, a Python bridge and an ACE-Step Colab notebook. Its separate React web demo plays oscillator-generated instrumentals; that demo does not synthesize lyrics into singing. We integrated the **official GPU API approach** into this existing website, preserving both subjects and all 91 topics. See [the inspection report](docs/UPLOADED_APP_REVIEW.md).

1. Open [our free singing notebook in Colab](https://colab.research.google.com/github/TechWhizSS/Intelligent_Tutoring/blob/codex/development/notebooks/Free_Singing_GPU.ipynb). Sign into your own Colab account. Choose **Runtime → Change runtime type → T4 GPU**; run cells 1–4. Free GPU availability and session limits apply; no paid upgrade or Google AI API is required.
2. Cell 3 requests actual 30-second Calculus and BEEE songs and displays audio for listening. Set `LANGUAGE = 'hi'` and rerun to test Hindi. These are live model calls, not bundled demo recordings. Academic meaning and pronunciation need listening review.
3. Cell 4 downloads **song-service.env**, containing your temporary HTTPS service URL and a private notebook key. Keep the notebook open. Do not paste the key into chat or commit the file.
4. Start this website, sign in as the demo admin, open **Connections**, select that connection file and click **Connect and test GPU**. This authenticates before saving the configuration. Students cannot configure or read the private connection. No terminal editing is needed for this step; a phone file picker works.
5. In Song studio choose a subject/topic and English or Hindi, generate/edit lyrics and click **Synthesize sung music**. The website submits the official `/release_task`, polls `/query_result`, fetches the actual `/v1/audio` WAV, and exposes it through the existing authenticated player/library/downloads.

Cloud network settings must allow the notebook’s `*.trycloudflare.com` tunnel (or its exact hostname, printed by cell 4). Current network restrictions still apply; the adapter does not bypass them. The notebook itself needs GitHub, PyPI, model download and Cloudflare access in Colab. If the session disconnects, rerun its startup/tunnel cells and upload the fresh file. A successful connection test verifies API authentication; it does not certify song generation or singing quality.

Private settings live in `runtime/music-service.json` (mode 0600, Git-ignored), or `APP_DATA_DIR` when configured. **Use local CPU engine** removes the uploaded GPU connection. For an existing official local server, export `LOCAL_MUSIC_URL=http://127.0.0.1:8001` and `LOCAL_MUSIC_API_KEY` before starting; host variables take precedence. Do not point this adapter at the Android bridge on port 8787: it expects the official ACE-Step API on port 8001.

## Legacy local CPU backend (developer reference)

The model download is a one-time setup step. Inference then runs offline.

1. Allow outbound GitHub and Hugging Face access in the cloud environment. Weight downloads may redirect to `*.hf.co` (including Xet/CDN hosts). The cloud proxy must permit the actual download hosts. No billing is involved.
2. Install a C++17 compiler (`g++`), git and Python 3.12+.
3. Run:

```sh
python3 scripts/setup_free_music.py
python3 scripts/check_providers.py
python3 -m app.server
```

The setup script pins the C++ source revision, builds the CPU engine, resolves the public model revision, downloads three GGUF files and verifies each public LFS SHA-256 checksum. It preserves `.part` files for interrupted downloads. The selected quantized model set is smaller than the upstream full default; no large language model is loaded.

Separate phases are available:

```sh
python3 scripts/setup_free_music.py --build-only
python3 scripts/setup_free_music.py --models-only
```

On this particular workspace the compiled engine is already present through `runtime/free-music/acestep.cpp`; only the model download remains blocked. This runtime installation is not committed; other checkouts should run the setup script.

Optional environment settings:

```text
FREE_MUSIC_DEVICE=CPU
FREE_MUSIC_THREADS=2
FREE_MUSIC_TIMEOUT=1800
```

`FREE_MUSIC_HOME`, `FREE_MUSIC_ENGINE` and `FREE_MUSIC_MODELS` can select another local installation. No secret is required. CPU inference may take many minutes. Start with a **30-second song**; one generation is allowed at a time to avoid exhausting RAM. The observed cloud host has 8 GB RAM and two allocated CPU cores, with no GPU. Successful inference performance has not yet been measured on it.

## Make a song with Gemini

1. Select Calculus or BEEE, chapter/topic, English or Hindi and music preferences.
2. Generate and edit a supplemental source-linked lyric draft, then choose **Generate with Lyria**.
3. The prompt is copied and Gemini opens in the same tab. Choose **Create music**, paste and send. If clipboard access is denied, copy the displayed prompt manually before opening Gemini.
4. Listen in Gemini. Download an MP3 where permitted, return to the saved chapter and use **Attach your own permitted audio** to play/download it in this library.

Gemini controls available models, song lengths, eligibility and free quotas. The app does not automatically prefill Google’s page, click Generate, import audio or claim an API integration.

## Other working features

The app includes source-linked chapter notes/formula summaries, supplemental worked examples and Hindi explanations, two supplemental quiz questions per topic with feedback, saved quiz attempts, editable/saved lyrics, a persistent song library, authenticated byte-range audio delivery and downloads, admin uploads/review, and all 91 rows in the syllabus readiness report. Complete textbook notes were not uploaded; they are not falsely marked ready.

Admins can upload PDF/TXT/MD/CSV originals and academic excerpts. Excerpts become supplemental chapter material only after review/approval; they never act as code or application instructions. Uploaded originals, BEEE lecture/lab scope, course outcomes and Calculus song associations are preserved. Popular-song mappings are metadata only, never copied recordings.

**Export song prompt** and permission-confirmed audio uploads remain available as optional utilities. The current music path is the Gemini handoff described above.

## Verification

```sh
python3 -m compileall -q app scripts tests
node --check static/app.js
python3 -m unittest discover -s tests -v
```

Node is optional for syntax checking. Runtime Python has no pip dependencies. Browser tests:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 tests/browser_smoke.py
```

Tests cover local paid-key/network independence, the official GPU REST contract, private authenticated connection storage, safe download origins, notebook syntax, exact local model inputs, shell-free process execution, missing models, timeouts, invalid audio, serial generation, both subjects/languages, lyric saving, quizzes, all report rows, downloads, playback/seeking, uninterrupted navigation, phone/tablet layout and admin review. Test WAVs and mocked model files are isolated fixtures and never bundled or presented as AI songs. Browser checks do not prove model singing quality. GitHub Actions repeats the application and browser checks.

## Catalogue and architecture

[Every topic and readiness status](docs/SYLLABUS_COMPLETENESS.md) · [CSV](docs/syllabus-completeness.csv)

```sh
python3 -m pip install openpyxl==3.1.5
python3 scripts/import_syllabus.py
python3 scripts/build_report.py
```

- `app/server.py`: API, sample sessions, jobs, uploads, audio and reports.
- `app/providers.py`: free local model readiness, native requests and CPU subprocess inference.
- `app/content.py`, `data/`, `sources/`: uploaded hierarchy, formulas, original featured lyrics and labelled supplemental material.
- `static/`: responsive dependency-free browser UI.
- `scripts/setup_free_music.py`: reproducible free engine/model setup.
- `tests/`: catalogue/API/local-engine contract and browser verification.

This is a single-process college-demo server. Sample passwords intentionally do not verify a college identity. Do not store real student records. A server restart marks unfinished generations failed; retry them from the library. `main` remains unchanged until the owner approves a merge.
