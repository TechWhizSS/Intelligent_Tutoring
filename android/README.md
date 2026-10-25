# Syllabus to Song — Android Sunrise edition

Native Android app adapted from the user-uploaded `design-experience-main (1).zip`, with the website's Semester I curriculum and sunrise visual direction. Android 8.0 or later is required. This is a college demonstration build, not a Play Store release.

## What is included

- SAP ID sample login: 3–30 letters/digits/underscores/hyphens and any nonempty password. Use the sample-account button, or `admin` for device-local material review. This is not college identity verification. Passwords are not saved.
- MBA Tech → CE → First year → Semester I selectors; all **38 Calculus + 53 BEEE topics** in uploaded order, with the same formulas, source excerpts, unit names, source locators and available objectives as the website.
- English/Hindi only. Editable source-linked supplemental lyric templates, music style, mood, vocal delivery, BPM, length, difficulty, formula repeats and custom instructions.
- Direct connection to an owner-run official ACE-Step GPU API, replacing the uploaded app's fixed emulator-only bridge. Import `song-service.env` from the free notebook or enter its HTTPS origin and private connection key.
- Gemini/Lyria browser handoff as an alternative: copy prompt, open Gemini, choose Create music, paste and send. Gemini eligibility and free quotas apply. There is no automatic prefill, Generate click or audio import.
- Device-local drafts, audio history, favourites, foreground play/pause/seek/replay, device-volume controls, permitted audio import and export using Android's file picker.
- Source summaries, formula references, labelled supplemental Hindi explanations/examples, objectives where supplied, two supplemental quizzes per topic/language with saved scores, and a completeness report showing every uploaded topic.
- Sample administrator excerpt upload/review and approved supplemental notes. These are device-local excerpts, not a cloud document-management system or full PDF/OCR extraction.

The original uploaded native player's MediaPlayer lifecycle and the SQLite song library were retained and adapted. Existing website routes and functionality remain intact. The app's library is independent of the website; cloud sync is not configured. Playback is foreground-only and stops when its player is left/backgrounded.

## Get actual ACE-Step audio

1. On your phone/computer, open the app's **More → Music connection → Open free GPU notebook**. The notebook is [Free_Singing_GPU.ipynb](https://colab.research.google.com/github/TechWhizSS/Intelligent_Tutoring/blob/codex/development/notebooks/Free_Singing_GPU.ipynb).
2. In your own Colab account, choose an available T4 GPU and run the notebook cells. Free GPUs are limited; a session can be unavailable or disconnected. No paid upgrade or purchased music API key is required by this app.
3. Download `song-service.env` from the notebook. In the app choose **Import song-service.env**. This file contains your own temporary service origin and private connection key. It is parsed as data, never executed. Do not paste the key into chat.
4. A successful check authenticates `/query_result`; it does **not** prove that a song can be generated. The key is encrypted at rest using Android Keystore/AES-GCM. The service must remain running.
5. In Studio choose a chapter and language, generate/edit/save lyrics, then tap **Synthesize with ACE-Step**. Keep the app open while it submits `/release_task`, polls `/query_result` and downloads the real WAV from the configured origin's `/v1/audio`.
6. When audio is returned, play it and review vocals, formula conditions and pronunciation. Export it through Android's file picker. Network/GPU/invalid-file errors remain visible; no TTS, oscillator audio or fixture is substituted.

BPM, duration and vocal language use the model's native fields. Genre/mood/voice/difficulty/repetition guide the prompt; exact delivery is not promised. The phone does not run the model. A working GPU backend is still needed. No actual educational song or singing quality has been verified in this cloud workspace.

## Build in Android Studio or the cloud

Use JDK 21, Android SDK 36, build-tools 36.0.0 and the provided Gradle wrapper. From the repository root:

```sh
python3 scripts/build_android_content.py
cd android
./gradlew --no-daemon :app:assembleDebug :app:testDebugUnitTest :app:lintDebug
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. It is debug-signed for demonstration installation. Android may ask you to allow installation from your browser/files app. A previously installed copy signed by a different developer requires uninstalling first; export any recordings you need before uninstalling.

`local.properties`, SDK/JDK binaries, Gradle caches, private connection files and keystores are ignored. Do not copy this cloud workspace's SDK path into another computer. Android Studio writes its own `local.properties`.

GitHub Actions builds/tests the native app and uploads the APK as an artifact. The committed downloadable demonstration APK, when present under `downloads/`, comes from a tested cloud build; `downloads/build.json` records its source tree and checksum. No credentials, real student records, uploaded private material or test songs are bundled.

## Verification boundaries

Python checks compare **every topic**, academic excerpt, objective, source locator, bilingual lyric template and quiz to the website's verified imported catalogue. JVM tests cover connection-file parsing, HTTPS/key requirements, exact reviewed lyric/native music requests, task IDs, supported result shapes and constrained audio download paths. Robolectric/Compose interaction tests exercise sample login, drafts for both subjects, notes, quizzes, the all-topic report and offline draft/score persistence. Compile/lint checks validate Android API use and packaging.

The cloud host has no Android device or KVM-accelerated emulator. Robolectric UI checks do not replace a physical-device, audio-decoder or live-GPU singing test. Real API results must pass WAV/MediaMetadataRetriever validation before appearing in the library.

## Source provenance

Uploaded archive SHA-256: `680d9afbdf4a30dc5a29621d1d86a38021d4d4d2a1a36679d11cce1d10b89d20`.

Reused/adapted components: Gradle Android scaffold, `MainActivity`, `SessionViewModel`, SQLite song database/DAO/repository/record, native audio import/player and library/history screens. The course-specific flow, account screen, curriculum loader, music protocol and theme were replaced for this project's approved scope. Academic material is generated reproducibly from the repository's existing verified uploaded sources with `scripts/build_android_content.py`.
