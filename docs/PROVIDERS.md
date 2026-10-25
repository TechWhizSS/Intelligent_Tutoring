# Free ACE-Step music: implementation and evidence

Updated 25 October 2026 after the instruction to use only free resources. All paid music-service adapters have been removed. No Google AI API, ElevenLabs or paid inference service is used. An optional user-run Colab GPU is accessed only through its owner-configured ACE-Step tunnel.

## Selected open-source implementation

- [ACE-Step 1.5 original model](https://github.com/ace-step/ACE-Step-1.5)
- [acestep.cpp CPU implementation and documented local API](https://github.com/ServeurpersoCom/acestep.cpp)
- Pinned C++ source revision: `de858d8e1a94f0e1939cf9bdd8ff7d9631953077`
- [Public quantized models](https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF)

The selected model files are `acestep-v15-turbo-Q4_K_M.gguf`, `Qwen3-Embedding-0.6B-Q8_0.gguf` and `vae-BF16.gguf`. This is a pure DiT synthesis path without the optional language model, chosen to reduce RAM use. CPU execution is supported upstream; acceptable latency/quality on this host remains unmeasured.

The app creates a private request JSON containing exact edited lyrics, music caption, BPM, duration, English/Hindi vocal language, eight turbo inference steps and WAV output. It invokes the local executable through an argument array with no shell, one request at a time, and reads the actual `request0.wav` output. There is no TTS fallback, external-key fallback or test-fixture fallback. Output validation checks a real WAV container and meaningful duration; this does not certify that the audio contains accurate lyrics or good singing.

BPM, duration and language use native fields. Genre, mood, vocal delivery and repeated formulas are caption preferences. Final singing and formula pronunciation require listening review. Lyrics are locally assembled source-linked templates with short curated examples; the interface does not pretend an LLM generated them.

## What was actually done here

- Inspected the host: 8 GB memory limit, two allocated CPU cores, no GPU.
- Checked the official free Hugging Face demo and API: proxy connection denied with HTTP 403.
- Downloaded the C++ source and ggml dependency through allowed GitHub access.
- Installed the free CMake build tool and successfully compiled `ace-synth` and `ace-server` for CPU.
- Executed the built binary and confirmed the expected CLI options.
- Ran `scripts/setup_free_music.py --models-only`: failed before the first model download with `Tunnel connection failed: 403 Forbidden`.
- Built the in-website local-generation path, original Calculus/BEEE bilingual featured lyrics and a reproducible downloader with pinned source and public model checksums.

## Current blocker — network, not money

The cloud environment's enforced network policy is restricted and its custom allowlist is empty. It blocks `huggingface.co` and `*.hf.space`. Public model downloads may additionally require `*.hf.co`, including Xet/CDN hosts. The available environment tools only inspect configuration; they cannot change this allowlist. The user has been asked to enable access through the cloud environment settings.

No payment, paid account, provider key or subscription is needed. Once network access is enabled, run `python3 scripts/setup_free_music.py --models-only`, verify the installed model checksums, restart the website, and run `python3 scripts/demo.py --generate-audio --length 30` and the Hindi variant.

**Actual educational songs have not yet been generated in this environment.** Model files are missing, so vocals, melody, instrumentals, chorus quality and Hindi pronunciation cannot honestly be verified. Tests use isolated fixtures to validate the pipeline and player; those fixtures are never presented as songs. See [current readiness](provider-check.json).

## Attribution

`acestep.cpp` is distributed under its upstream open-source license; source and license files remain in its local checkout. ACE-Step model attribution and licensing remain with the original ACE-Step authors. The setup manifest records source revision, resolved model revision and file SHA-256 checksums. No third-party code, binary or multi-gigabyte model is committed into this application repository.


## Uploaded Android app technology: official GPU API

Inspected `design-experience-main.zip`: the real singing route uses ACE-Step 1.5 on a user-run GPU, `/release_task`, `/query_result`, and `/v1/audio`, with a bearer key. The React demo’s oscillators do not sing. We implemented a separate official REST adapter in `app/free_gpu.py` and a website-specific notebook in `notebooks/Free_Singing_GPU.ipynb`, without copying the Android app, adding its other languages, or replacing this website’s curriculum.

Verified the request names/statuses against upstream [API.md](https://github.com/ace-step/ACE-Step-1.5/blob/ca1e85fe9430179831e6bc6be790c332190a3866/docs/en/API.md) and inspected its loader at revision `ca1e85fe9430179831e6bc6be790c332190a3866`. The notebook pins that version and applies a guarded FP32 loader override for T4, because that pinned code does not implement the suggested generic dtype environment flag. CPU offload is enabled and the optional LM is disabled to reduce GPU requirements. Actual T4 memory usage/performance remains unverified.

The website administrator uploads the notebook connection file. Its URL is restricted to an HTTPS Cloudflare quick tunnel or the official local loopback service on port 8001. A public tunnel requires a private key. The server performs an authenticated empty-task query before saving, stores the private configuration with mode 0600 in ignored runtime storage, never returns the key to students, never forwards credentials on redirects, and fetches audio only from the configured origin’s `/v1/audio`. Configuration changes are blocked during generation. Authentication failures, network restrictions, GPU failures, missing output, invalid WAVs and timeouts remain visible errors.

No paid model subscription is introduced. Colab is a Google-hosted compute notebook, **not a Google AI API integration**. Free GPUs are limited and can be unavailable or disconnected. An account owner must start the notebook and retain its session. Codex cannot sign into that account or allocate a Colab GPU on their behalf. This cloud host must permit the generated tunnel host; existing network restrictions are not bypassed.

**Verification boundary:** REST/security tests use clearly isolated fixtures. The notebook cells compile and the browser connection UI is tested. No user-run GPU is currently connected, no live song has been returned here, and notebook execution, vocals and musical quality are not claimed verified. The free local CPU option remains available when its model downloads are allowed.
