---
workflow: general-video
flow: automation
storyboard: yes
message: "data-peek speaks ClickHouse now (beta)"
destination: social-feed
aspect: 1920x1080
language: en
length: 60s
audience: developers on X, Threads, and LinkedIn
---

## Intent

A ~60 s launch cut for ClickHouse support (beta, v0.33.0), made from Rohith's own narrated screen
recording with his face cam. His voice is the only narration. Quiet confidence, data-peek brand.

## Assets

- assets/click-house-demo.mp4 — Rohith's 2:47 narrated recording (1680x1080, face cam baked in); source of every footage segment.
- assets/transcript.json — whisper small.en word timings of the recording; caption source.
- assets/music.mp3 — the v026 tour music bed (49.9 s), reused under the voice.
- design.md, logo.svg, fonts/ — the data-peek video design system from motion-kit.

## Customizations

- Burned-in captions from his transcript, ASR errors fixed (Datapix -> data-peek, click house -> ClickHouse); his words otherwise verbatim.
- Motion open title and end card: "ClickHouse support is in beta. Query and browse it in data-peek, free for personal use." + datapeek.dev.

## Notes

- No HeyGen, no AI avatar, no AI voice (community feedback on earlier launches).
- Callouts show only facts visible on screen: 20M events, "11 rows returned 301ms" over the full table, Explain total 17ms and PrimaryKey granules 17/1583, real ClickHouse type names.
- Drop his "a million rows" line (the table has 20M) and "not all the tools expose" (no competitor framing).
