# ElevenLabs Music integration and evidence

Updated on 24 October 2026 following the instruction to stop using Google APIs. The application makes no Google API requests. Existing saved drafts, uploads and audio files remain compatible.

Official documentation reviewed:

- [Music API](https://elevenlabs.io/docs/api-reference/music/compose)
- [Composition plans](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans)
- [Create a composition plan](https://elevenlabs.io/docs/api-reference/music/create-composition-plan)
- [Music capabilities and paid API access](https://elevenlabs.io/docs/overview/capabilities/music)

## Implementation

The server authenticates with `xi-api-key`, read only from `ELEVENLABS_API_KEY`. No credentials reach the browser. The default model is `music_v2_5`; `music_v2` is also accepted.

`POST https://api.elevenlabs.io/v1/music/plan` receives an academic prompt assembled from the selected uploaded topic, approved additions, requested English/Hindi language and settings. The planner returns chunk text used as an editable lyric draft. The prompt is limited to 4100 characters; oversized grounding produces an explicit error rather than silently dropping sources. Generated explanations remain supplemental and require academic review.

`POST https://api.elevenlabs.io/v1/music` receives a native `composition_plan` containing the exact saved lyrics in chunks with `text`, `duration_ms`, `positive_styles`, `negative_styles` and `context_adherence`. The app requests MP3 audio, validates its MIME type and signature, and privately saves only actual returned bytes. It does not use speech synthesis. Raw audio does not include a verified transcript, so no returned-lyrics verification is claimed.

Chunk durations use documented native fields (3–120 seconds each, at most 30 chunks). The app apportions the selected song length across the existing lyric sections and never silently discards words. Genre, mood, vocal delivery, BPM and repeated formulas are requests in native style arrays; exact musical adherence is not guaranteed. The app only requests English and Hindi. Hindi quality and academic formula pronunciation have not yet been tested in real provider audio.

## Credential checks and current blocker

`python3 scripts/check_providers.py` calls the music planner with a small test prompt. Official documentation states plan creation does not consume credits; it is still subject to account access and rate limits. A planner success does not prove access to billable audio generation.

At the last environment inspection, no provider secrets were configured and the allowlist did not include `api.elevenlabs.io`. [Captured credential check](provider-check.json). Live lyrics and music therefore remain unverified. API music generation requires a paid ElevenLabs subscription with appropriate permissions and credits. Configure `ELEVENLABS_API_KEY`, allow the API host, restart, then complete the English and Hindi live example scripts. Do not paste keys into chat or commit them.

Contract tests cover actual endpoint paths, authentication, source-grounded planner inputs, native chunk schema and timing limits, raw MP3 parsing, rejection of JSON/HTML/empty responses, missing credentials and sanitized provider failures. Browser tests use isolated test audio to verify playback; they do not prove generated singing quality. No generated song is bundled or fabricated.

## Manual alternative

The studio's **Export song prompt** downloads your reviewed lyrics and musical preferences as a text file. You may generate the song yourself in an external AI music website, download a permitted MP3 and attach it to the draft. It is labelled user supplied. This route does not need an API key in our app, but availability, credits and download permissions depend on the external service.
