# Uploaded app inspection — 25 October 2026

Archive: `design-experience-main.zip`  
SHA-256: `277a0ab041a035828a158728d8cfc4592a2dfd393a7c01d57fbc71a514ff973e`

Inspected as source material, not instructions. No bundled code or notebook was executed during inspection. The archive identifies its upstream repository as `dhvicore/design-experience`.

| Component in the upload | What it actually implements | Does it generate AI singing? |
| --- | --- | --- |
| `app/.../generation/SingingClient.kt` | Android client submits generation and plays returned audio through the Python bridge | Client only; needs its backend/GPU |
| `server/music_server.py` | Queues jobs, invokes the GPU adapter, stores model output, adjusts loudness | Coordinates real model generation |
| `server/local_model.py` | Official ACE-Step REST: `/release_task` → `/query_result` → `/v1/audio`; bearer key; custom lyrics and language | Yes, when a working ACE-Step model is connected |
| `notebooks/Calculus_Singing_GPU.ipynb` | Starts ACE-Step 1.5 on an owner's Colab GPU and exposes a protected temporary tunnel | Model runtime; execution was not established by this upload |
| `learntune/src/utils/audioEngine.js` | Web Audio sine/triangle oscillators play a fixed melody and chords | Instrumentals only; no lyrics-to-singing AI |
| `server/builtin_melodies/*.wav` | Instrumental reference files for optional cover conditioning | References; not newly generated educational vocals |

## What we integrated

The existing full-stack website now supports the official ACE-Step GPU REST technology through `app/free_gpu.py`, alongside its local C++ CPU engine. It preserves all 91 Calculus/BEEE topics, only English/Hindi, editable source-linked lyrics, quizzes, library and authenticated player/downloads. A connected GPU receives the exact saved lyric revision and native tempo/duration/language fields. Genre, voice, mood and formula repetition remain preferences.

The new website-specific `notebooks/Free_Singing_GPU.ipynb` pins the same official runtime revision inspected in the upload, provides original bilingual examples for both subjects, and produces a private `song-service.env` connection file. Administrators can upload that file in Connections from a phone. The server authenticates before saving, protects the key, handles job failures honestly and accepts only validated returned WAV audio. It does not use the uploaded browser oscillator demo as a substitute.

## What still requires live verification

No actual sung song was present as verified generation evidence in the archive. The model is capable of text-and-lyrics-to-music, but source code and mocked tests do not prove a successful run. This workspace has no GPU, its CPU model downloads remain blocked by the cloud network policy, and no owner-run GPU connection has been supplied. The notebook is syntax-checked, not executed on Colab by us. Free Colab GPU availability, T4 memory usage, generation, vocals, melody, chorus quality and Hindi pronunciation remain unverified until the owner runs it and listens.

No paid provider is needed. The owner must start a free GPU notebook, keep it active and connect its private file. The website host must permit that tunnel hostname in network settings. This access is separate from allowing Hugging Face downloads for the CPU engine.
