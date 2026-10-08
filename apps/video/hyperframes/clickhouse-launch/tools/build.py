"""Generate index.html for the ClickHouse launch cut.

Cut decisions live in SEGMENTS (source word ranges from assets/transcript.json); everything else
(timeline positions, caption groups, callout times) is derived, so a re-cut is a one-line edit here
followed by `python3 tools/build.py`.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = json.loads((ROOT / "assets/transcript.json").read_text())
WORDS = WORDS if isinstance(WORDS, list) else WORDS["words"]

OPEN_DUR = 3.0
END_DUR = 5.5
END_XFADE = 0.4
FOOT_X, FOOT_W, W, H = 120, 1680, 1920, 1080

# (id, first word start, last word start) in source seconds
SEGMENTS = [
    ("s1", 11.80, 14.50),
    ("s2", 23.40, 29.49),
    ("s3a", 37.68, 38.66),
    ("s3b", 41.92, 48.01),
    ("s4", 52.92, 65.95),
    ("s6", 83.30, 91.04),
    ("s7", 98.64, 105.44),
    ("s8", 135.67, 138.27),
    ("s9", 149.60, 152.70),
]

FIXES = {"Datapix": "data-peek", "proctop": "top", "explain,": "Explain,", "markdown.": "Markdown."}
TOP_CAPTION_WORD = "milliseconds,"


def word_index(t):
    return min(range(len(WORDS)), key=lambda i: abs(WORDS[i]["start"] - t))


def segment_bounds(first, last):
    i, j = word_index(first), word_index(last)
    prev_end = WORDS[i - 1]["end"] if i > 0 else 0
    next_start = WORDS[j + 1]["start"] if j + 1 < len(WORDS) else WORDS[j]["end"] + 1
    src_in = max(WORDS[i]["start"] - 0.12, prev_end + 0.02)
    src_out = min(WORDS[j]["end"] + 0.18, next_start - 0.05)
    return i, j, round(src_in, 3), round(src_out, 3)


def caption_tokens(i, j):
    toks = []
    k = i
    while k <= j:
        text = WORDS[k]["text"].strip()
        if text.lower() == "click" and k + 1 <= j and WORDS[k + 1]["text"].strip().lower().startswith("house"):
            tail = re.sub(r"(?i)^house", "", WORDS[k + 1]["text"].strip())
            toks.append({"text": "ClickHouse" + tail, "start": WORDS[k]["start"], "kw": True})
            k += 2
            continue
        text = FIXES.get(text, text)
        toks.append({"text": text, "start": WORDS[k]["start"], "kw": text.startswith("data-peek")})
        k += 1
    if not toks[0]["text"].startswith("data-peek"):
        toks[0]["text"] = toks[0]["text"][0].upper() + toks[0]["text"][1:]
    if toks[-1]["text"][-1] in ",":
        toks[-1]["text"] = toks[-1]["text"][:-1] + "."
    elif toks[-1]["text"][-1] not in ".?!":
        toks[-1]["text"] += "."
    return toks


def group_tokens(toks, max_chars=40):
    """Sentences first, then split long sentences at commas, then by length."""
    sentences, cur = [], []
    for t in toks:
        cur.append(t)
        if t["text"][-1] in ".?!":
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)

    def width(ts):
        return len(" ".join(x["text"] for x in ts))

    groups = []
    for sent in sentences:
        if width(sent) <= max_chars:
            groups.append(sent)
            continue
        line = []
        for t in sent:
            if line and width(line + [t]) > max_chars:
                groups.append(line)
                line = []
            line.append(t)
            if t["text"].endswith(",") and width(line) >= 14:
                groups.append(line)
                line = []
        if line:
            if groups and width(line) < 16 and width(groups[-1] + line) <= max_chars + 8:
                groups[-1].extend(line)
            else:
                groups.append(line)
    return groups


cursor = OPEN_DUR
clips = []
for sid, first, last in SEGMENTS:
    i, j, src_in, src_out = segment_bounds(first, last)
    dur = round(src_out - src_in, 3)
    clips.append({"id": sid, "i": i, "j": j, "src_in": src_in, "src_out": src_out, "start": round(cursor, 3), "dur": dur})
    cursor += dur
END_START = round(cursor - END_XFADE, 3)
TOTAL = round(END_START + END_DUR, 3)


def g(src, sid):
    c = next(c for c in clips if c["id"] == sid)
    return round(c["start"] + (src - c["src_in"]), 3)


def clip_end(sid):
    c = next(c for c in clips if c["id"] == sid)
    return round(c["start"] + c["dur"], 3)


def lane(points):
    return json.dumps({"version": 1, "lanes": [{"target": "volume", "points": [{"t": round(t, 3), "v": v} for t, v in points]}]})


video_html = []
for n, c in enumerate(clips):
    last = n == len(clips) - 1
    fade_out = END_XFADE if last else 0.06
    pts = [(0, 0), (0.04, 1), (c["dur"] - fade_out, 1), (c["dur"], 0)]
    video_html.append(
        f'      <video id="v-{c["id"]}" class="clip footage" src="assets/click-house-demo.mp4" playsinline '
        f'data-has-audio="true" data-audio-group="voice" data-start="{c["start"]}" data-duration="{c["dur"]}" '
        f'data-media-start="{c["src_in"]}" data-track-index="2" data-automation=\'{lane(pts)}\'></video>'
    )

caption_html, caption_words = [], []
for c in clips:
    toks = caption_tokens(c["i"], c["j"])
    groups = group_tokens(toks)
    for gi, grp in enumerate(groups):
        gs = g(grp[0]["start"], c["id"]) if gi else c["start"]
        ge = g(groups[gi + 1][0]["start"], c["id"]) if gi + 1 < len(groups) else clip_end(c["id"])
        top = any(t["text"] == TOP_CAPTION_WORD.rstrip(",") + "." or t["text"] == TOP_CAPTION_WORD for t in grp)
        spans = []
        for t in grp:
            ts = g(t["start"], c["id"])
            cls = "w kw" if t["kw"] else "w"
            spans.append(f'<span class="{cls}" data-t="{ts}">{t["text"]}</span>')
        cid = f'cap-{c["id"]}-{gi}'
        caption_html.append(
            f'    <div id="{cid}" class="clip cap{" top" if top else ""}" data-start="{gs}" data-duration="{round(ge - gs, 3)}" '
            f'data-track-index="6"><div class="cap-box">{" ".join(spans)}</div></div>'
        )

cue = {
    "count_in": g(37.75, "s3a"),
    "count_out": g(45.40, "s3b"),
    "ms_card": g(65.45, "s4"),
    "ms_end": clip_end("s4"),
    "types_zoom": g(83.55, "s6"),
    "types_chip": g(84.00, "s6"),
    "types_end": clip_end("s6"),
    "plan_push": g(100.60, "s7"),
    "plan_card": g(104.30, "s7"),
    "plan_end": clip_end("s7"),
    "md_chip": g(136.60, "s8"),
    "md_end": clip_end("s8"),
    "end": END_START,
    "total": TOTAL,
}
cue["count_dur"] = round(cue["count_out"] - cue["count_in"], 3)


def zoom_offset(tx, ty, scale):
    """Counter-translate (nested wrappers: T = -offset), clamped so the scaled footage still fills the frame."""
    half_w, half_h = W / 2 / scale, H / 2 / scale
    cx = min(max(tx, FOOT_X + half_w), FOOT_X + FOOT_W - half_w)
    cy = min(max(ty, half_h), H - half_h)
    return round(W / 2 - cx, 1), round(H / 2 - cy, 1)


ZOOMS = {
    "types": (1.8, *zoom_offset(FOOT_X + 0.65 * FOOT_W, 0.465 * H, 1.8)),
    "plan": (1.35, *zoom_offset(FOOT_X + 0.80 * FOOT_W, 0.50 * H, 1.35)),
}

music_a_dur = 49.9 - 0.05
music_b_start = 48.4
music_b_dur = round(TOTAL - music_b_start, 3)
BED, LIFT = 0.16, 0.5
music_a = lane([(0, 0), (0.3, LIFT), (2.8, LIFT), (3.4, BED), (music_b_start, BED), (music_a_dur, 0)])
eb = END_START - music_b_start
music_b = lane([(0, 0), (1.4, BED), (eb, BED), (eb + 0.8, LIFT), (music_b_dur - 1.2, LIFT), (music_b_dur, 0)])

template = (ROOT / "tools/index.template.html").read_text()
out = (
    template.replace("{{TOTAL}}", str(TOTAL))
    .replace("{{VIDEOS}}", "\n".join(video_html))
    .replace("{{CAPTIONS}}", "\n".join(caption_html))
    .replace("{{CUES}}", json.dumps(cue))
    .replace("{{ZOOMS}}", json.dumps(ZOOMS))
    .replace("{{END_START}}", str(END_START))
    .replace("{{END_DUR}}", str(END_DUR))
    .replace("{{MUSIC_A_DUR}}", str(round(music_a_dur, 3)))
    .replace("{{MUSIC_A_LANE}}", music_a)
    .replace("{{MUSIC_B_START}}", str(music_b_start))
    .replace("{{MUSIC_B_DUR}}", str(music_b_dur))
    .replace("{{MUSIC_B_LANE}}", music_b)
    .replace("{{COUNT_IN}}", str(cue["count_in"]))
    .replace("{{COUNT_DUR}}", str(cue["count_dur"]))
    .replace("{{MS_IN}}", str(cue["ms_card"]))
    .replace("{{MS_DUR}}", str(round(cue["ms_end"] - cue["ms_card"], 3)))
    .replace("{{TYPES_IN}}", str(cue["types_chip"]))
    .replace("{{TYPES_DUR}}", str(round(cue["types_end"] - cue["types_chip"], 3)))
    .replace("{{PLAN_IN}}", str(cue["plan_card"]))
    .replace("{{PLAN_DUR}}", str(round(cue["plan_end"] - cue["plan_card"], 3)))
    .replace("{{MD_IN}}", str(cue["md_chip"]))
    .replace("{{MD_DUR}}", str(round(cue["md_end"] - cue["md_chip"], 3)))
)
(ROOT / "index.html").write_text(out)

for c in clips:
    print(f'{c["id"]:4} src {c["src_in"]:7.2f}-{c["src_out"]:7.2f}  at {c["start"]:6.2f}-{c["start"] + c["dur"]:6.2f}')
print("end card", END_START, "total", TOTAL)
print(json.dumps(cue))
print(json.dumps(ZOOMS))

# Carve speech room into both music beds; build rewrites index.html, so the carve must follow it.
# Needs @hyperframes/core: set HF_CORE to a directory containing node_modules/@hyperframes/core.
import os
import subprocess

core = os.environ.get("HF_CORE")
carve = Path.home() / ".claude/skills/hyperframes-audio/scripts/carve.mjs"
if core and carve.exists():
    voices = [arg for c in clips for arg in ("--voice", f'v-{c["id"]}')]
    for bed in ("music-a", "music-b"):
        subprocess.run(["node", str(carve), "--comp", str(ROOT / "index.html"), "--bed", bed, *voices, "--core", core], check=True)
else:
    print("skipped carve: set HF_CORE to run it")
