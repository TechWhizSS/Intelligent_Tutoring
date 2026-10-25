# Syllabus to Song — Gemini music handoff

**Current hosted section 2:** **Generate with Lyria** prepares the selected chapter/language/settings and any edited lyrics, copies the prompt and opens Gemini in the same tab on mobile or desktop. In Gemini, select **Create music**, paste and send. No supported native Gemini URL-prefill contract was found; the app does not claim that the prompt is already pasted or that music mode is automatically selected. Clipboard denial reveals selectable prompt text and a direct link instead of losing the prompt. Actual audio is created/played in Gemini; permitted downloads can be attached to the chapter. ElevenLabs remains optional below, with its existing subscription restriction clearly displayed.

A full-stack educational music studio for **MBA Tech → CE → First year → Semester I**, with all 38 uploaded Calculus topics and 53 uploaded BEEE topics indexed in order. Only English and Hindi are supported.

The music backend is **ACE-Step 1.5**, an open-source text-and-lyrics-to-music model. Choose the **official API on your free Colab GPU**, using the same technology found in the uploaded Android app, or a local CPU through `acestep.cpp`. There is **no paid music API or subscription**. The GPU connection uses a private, locally generated key, not a purchased provider key. The app sends reviewed lyrics to the selected AI engine for sung vocals, melody and accompaniment. It never substitutes speech synthesis or a test fixture for a generated song.

**Current boundary:** the free CPU engine has been compiled in this Codex environment, but downloading its three public model files fails with proxy HTTP 403 because Hugging Face is blocked. No actual generated song or singing quality is claimed yet. The new GPU adapter and notebook are tested at the protocol/browser level; a user-run Colab GPU has not been connected or executed here. The website reports its setup state. See [provider evidence](docs/PROVIDERS.md) and [captured readiness](docs/provider-check.json).

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

## Use the uploaded app’s GPU technology (recommended)

The uploaded `design-experience-main.zip` contains an Android singing client, a Python bridge and an ACE-Step Colab notebook. Its separate React web demo plays oscillator-generated instrumentals; that demo does not synthesize lyrics into singing. We integrated the **official GPU API approach** into this existing website, preserving both subjects and all 91 topics. See [the inspection report](docs/UPLOADED_APP_REVIEW.md).

1. Open [our free singing notebook in Colab](https://colab.research.google.com/github/TechWhizSS/Intelligent_Tutoring/blob/codex/development/notebooks/Free_Singing_GPU.ipynb). Sign into your own Colab account. Choose **Runtime → Change runtime type → T4 GPU**; run cells 1–4. Free GPU availability and session limits apply; no paid upgrade or Google AI API is required.
2. Cell 3 requests actual 30-second Calculus and BEEE songs and displays audio for listening. Set `LANGUAGE = 'hi'` and rerun to test Hindi. These are live model calls, not bundled demo recordings. Academic meaning and pronunciation need listening review.
3. Cell 4 downloads **song-service.env**, containing your temporary HTTPS service URL and a private notebook key. Keep the notebook open. Do not paste the key into chat or commit the file.
4. Start this website, sign in as the demo admin, open **Connections**, select that connection file and click **Connect and test GPU**. This authenticates before saving the configuration. Students cannot configure or read the private connection. No terminal editing is needed for this step; a phone file picker works.
5. In Song studio choose a subject/topic and English or Hindi, generate/edit lyrics and click **Synthesize sung music**. The website submits the official `/release_task`, polls `/query_result`, fetches the actual `/v1/audio` WAV, and exposes it through the existing authenticated player/library/downloads.

Cloud network settings must allow the notebook’s `*.trycloudflare.com` tunnel (or its exact hostname, printed by cell 4). Current network restrictions still apply; the adapter does not bypass them. The notebook itself needs GitHub, PyPI, model download and Cloudflare access in Colab. If the session disconnects, rerun its startup/tunnel cells and upload the fresh file. A successful connection test verifies API authentication; it does not certify song generation or singing quality.

Private settings live in `runtime/music-service.json` (mode 0600, Git-ignored), or `APP_DATA_DIR` when configured. **Use local CPU engine** removes the uploaded GPU connection. For an existing official local server, export `LOCAL_MUSIC_URL=http://127.0.0.1:8001` and `LOCAL_MUSIC_API_KEY` before starting; host variables take precedence. Do not point this adapter at the Android bridge on port 8787: it expects the official ACE-Step API on port 8001.

## Enable free local CPU singing

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

## Make a song

1. Select Calculus or BEEE, chapter/unit, topic, English/Hindi and music preferences.
2. Click **Generate lyrics**. Drafts are free, source-linked local templates, clearly labelled supplemental and not LLM-generated. Rolle's Theorem and Electrical Circuit Elements include short, original bilingual featured lyrics; other topics use uploaded references and supplemental Hindi explanations.
3. Review/edit the lyrics and save. For a 30-second song keep the wording short; an AI may not deliver every word of a long chapter summary.
4. Click **Synthesize sung music**. The app invokes the selected local or connected GPU AI with the exact saved lyrics, native BPM, duration and vocal-language fields, plus a caption for genre, mood and delivery.
5. When actual audio exists, load it in the browser player, listen, seek and download the WAV. Check formula pronunciation, Hindi delivery and academic meaning before submission.

No model setup check certifies singing quality. Missing models, memory errors, timeouts and empty/invalid audio remain visible failures. Genre, voice, mood and formula repetition are model preferences; exact adherence is not promised.

To run both subject examples against a running website:

```sh
python3 scripts/demo.py
python3 scripts/demo.py --language hi
python3 scripts/demo.py --generate-audio --length 30
python3 scripts/demo.py --generate-audio --language hi --length 30
```

Sign in as `submission-demo` with any password to see these records. Actual generated outputs are saved to `runtime/demo-output/`. The `--live` spelling remains an alias for `--generate-audio`, with no paid provider behind it.

## Other working features

The app includes source-linked chapter notes/formula summaries, supplemental worked examples and Hindi explanations, two supplemental quiz questions per topic with feedback, saved quiz attempts, editable/saved lyrics, a persistent song library, authenticated byte-range audio delivery and downloads, admin uploads/review, and all 91 rows in the syllabus readiness report. Complete textbook notes were not uploaded; they are not falsely marked ready.

Admins can upload PDF/TXT/MD/CSV originals and academic excerpts. Excerpts become supplemental chapter material only after review/approval; they never act as code or application instructions. Uploaded originals, BEEE lecture/lab scope, course outcomes and Calculus song associations are preserved. Popular-song mappings are metadata only, never copied recordings.

**Export song prompt** and permission-confirmed audio uploads remain available as optional utilities. The primary generation path is ACE-Step through the website’s Synthesize button, using the selected CPU/GPU backend.

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


## Requested ElevenLabs CLI onboarding

Ran `npx -y @elevenlabs/cli@latest onboard init`. It stopped at `ask_user`:
this cloud runtime cannot receive its browser key handoff and requires a private
`ELEVENLABS_API_KEY` environment secret or `.env.local`. Its secret file was never
opened or printed. The user selected the Gemini fallback instead. `.env.local`
is ignored. CLI onboarding does not remove ElevenLabs Music API billing rules.
