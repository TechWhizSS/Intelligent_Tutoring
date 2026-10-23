# Google provider integration and evidence

Documentation checked on 24 October 2026 (Asia/Kolkata):

- [Official Lyria 3.5 music generation guide](https://ai.google.dev/gemini-api/docs/music-generation)
- [Official Generate Content music API guide](https://ai.google.dev/gemini-api/docs/generate-content/music-generation)
- [Lyria 3.5 model reference](https://ai.google.dev/gemini-api/docs/models/lyria-3.5)
- [Gemini text generation guide](https://ai.google.dev/gemini-api/docs/text-generation)

The documentation describes sung vocals, custom lyrics, melody and instrumental arrangements for `lyria-3.5`. The adapter uses the documented REST endpoint:

```text
POST https://generativelanguage.googleapis.com/v1beta/models/lyria-3.5:generateContent
x-goog-api-key: <server-side GEMINI_API_KEY>
Content-Type: application/json

{"contents":[{"role":"user","parts":[{"text":"<musical direction and custom lyrics>"}]}]}
```

The app iterates through the selected candidate's content parts, finds actual `inlineData` audio, validates base64 and supported MIME type, saves it privately, and records provider-returned lyrics separately. MP3 is the default provider output. It also accepts returned WAV. Missing audio, safety blocks, invalid credentials, model unavailability, billing/permission failures, quota errors and network failures never become fabricated tracks. Lyrics are sent as original custom lyrics, with instructions for singing rather than speech. There is no TTS fallback.

Gemini uses the same documented Generate Content REST structure, with server-controlled grounding instructions and the uploaded academic source plus approved excerpts. Defaults are configurable with `GEMINI_MODEL` and `LYRIA_MODEL`.

## Controls

| Control | Implementation | Guarantee |
| --- | --- | --- |
| English / Hindi | Requested in Gemini instructions and Lyria prompt | Review returned audio |
| Genre, mood, vocal delivery | Natural-language prompt preferences | No exact parameter-level enforcement |
| Tempo | Requested BPM in prompt | Not guaranteed |
| Length | Approximate seconds in prompt | Lyria determines final duration |
| Difficulty | Lyrics instruction | Supplemental output; review required |
| Formula repeats | Lyrics setting and repeat request in music prompt | Not guaranteed |
| Custom instructions | Bounded preference text subordinate to academic source | Must not override grounding |
| Editable lyrics | Saved text sent as custom lyrics | Listen and compare provider delivery |
| Play/download | Returned audio or permission-confirmed recordings | No fake generated songs |

Controls are not passed as invented API fields. RealTime instrumental generation and speech generation are not used.

## Current verification boundary

The cloud environment reports **zero configured secrets** and **zero outbound identities**. `GEMINI_API_KEY` is absent. Its restricted destination allowlist does not include `generativelanguage.googleapis.com`. The credential checker reports both models blocked before making authenticated requests. See [the captured check](provider-check.json).

Completed locally:

- Full catalogue and English/Hindi offline workflows for Calculus and BEEE.
- Provider request/response contract tests with mocks, including interleaved text/audio parts and explicit errors.
- A browser decoding, playing and downloading a test-only WAV in an isolated instance. This verifies the player, **not** Lyria output or sung quality.

Not completed: live Gemini lyrics, actual Lyria songs, listening verification of vocals/melody/chorus, language accuracy in provider audio, or provider download entitlement for a particular billing account. No generated song is bundled or claimed.

To unblock: configure a billed, authorized `GEMINI_API_KEY` in cloud environment secrets; allow the official API host; restart; run `python3 scripts/check_providers.py`; then run `python3 scripts/demo.py --live` and its Hindi variant. Model metadata access alone does not prove generation. Review resulting songs before a college presentation.
