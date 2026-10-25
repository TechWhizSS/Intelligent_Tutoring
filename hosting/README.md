# Browser hosting adapter

The Python website remains unchanged as the local/full CPU implementation.
This adapter packages its current UI, all 91 syllabus topics, English/Hindi
lyric templates, quizzes, supplemental notes and uploaded originals for Sites.

`worker.mjs` implements the same HTTP API on Cloudflare Workers. Durable R2
records replace local SQLite/files only in the hosted edition. Sites owns the
outer owner-private ChatGPT sign-in; the requested sample SAP login remains
inside the app. Records are isolated by the Sites visitor ID and SAP ID.

The current interface offers **Generate with Lyria** as its only music route:
it copies the chapter prompt and opens Gemini, where the user selects Create
music, pastes and sends. No native URL prefill or automatic audio import is
claimed. A permitted downloaded MP3 can be attached to a saved lyric draft.

The hosted edition retains administrator material uploads/review, editable
lyrics, audio persistence, byte-range downloads and the complete syllabus
report. Legacy ACE-Step API routes remain for existing records and protocol
tests, but have no generation/setup controls in the interface. The retired
provider adapter and account-check route are removed; loading provider status
deletes its old private credential for that visitor. It never fabricates audio.

## Reproduce the package and tests

```sh
python3 hosting/build_site.py /tmp/syllabus-hosted
node hosting/test_worker.mjs /tmp/syllabus-hosted/worker/index.js
```

The builder copies only approved source files and generated public curriculum
content, never runtime databases, student records, connection files or keys.
`test_worker.mjs` exercises the real hosted routes with isolated in-memory R2
and GPU fixtures. Its WAV is not a generated educational song.

Production uses the managed Site's tracked `.openai/hosting.json`, R2 binding
`BUCKET`, a Worker ESM artifact and its separate managed source repository.
Hosting credentials are short-lived, handled only through stdin/process memory,
and are never committed. The original GitHub changes stay on
`codex/development`; `main` is untouched.
