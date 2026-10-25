# Browser hosting adapter

The Python website remains unchanged as the local/full CPU implementation.
This adapter packages its current UI, all 91 syllabus topics, English/Hindi
lyric templates, quizzes, supplemental notes and uploaded originals for Sites.

`worker.mjs` implements the same HTTP API on Cloudflare Workers. Durable R2
records replace local SQLite/files only in the hosted edition. Sites owns the
outer owner-private ChatGPT sign-in; the requested sample SAP login remains
inside the app. Records are isolated by the Sites visitor ID and SAP ID.

The hosted edition supports administrator uploads/review, private notebook
connection uploads, the official free ACE-Step API, editable lyrics, asynchronous
job polling, audio persistence, byte-range downloads and the complete syllabus
report. It cannot execute the C++ CPU model in a Worker; it clearly requires a
connected GPU before synthesis. It never fabricates audio.

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
