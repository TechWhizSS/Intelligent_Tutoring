# Syllabus to Song — compact final report

**Both deliverables were built: the responsive website and the native Android app.**

- [Compact illustrated report (PDF, 3 pages)](Syllabus_to_Song_Compact_Report.pdf)
- [Editable report (Word)](Syllabus_to_Song_Compact_Report.docx)
- [Open the website](https://syllabus-to-song-studio.aptcat4096.chatgpt.site)
- [Download the Android APK](https://github.com/TechWhizSS/Intelligent_Tutoring/raw/refs/heads/codex/development/android/downloads/SyllabusToSong-v1.0-sunrise.apk)

The report covers both interfaces, curriculum, key features, screenshots, delivered links, verification and the remaining audio-generation boundary. It includes 8 actual UI screenshots. Additional captures are in `screenshots/`.

Website captures use the current application code in Chromium with isolated sample drafts and no generated/fixture audio. Android captures render the actual Compose screens in Robolectric with Android SDK 35 native graphics; they are not physical-device screenshots. See `capture-provenance.json`.

Actual AI educational singing has not been verified. Gemini remains a manual external-browser route. The native ACE-Step route needs an owner-run GPU and an actual generation/listening test. Full textbook notes were not supplied; supplemental material is labelled. The website is currently owner-private.

To rebuild the documents from the saved captures, install `reportlab`, `python-docx` and `Pillow`, then run `python3 scripts/build_project_report.py`. The PDF uses Open Sans from `/usr/share/fonts/truetype/open-sans/`. `scripts/capture_report_website.py` can refresh the browser images using Playwright/Chromium.
