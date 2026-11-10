#!/usr/bin/env python3
"""Synthesize episode audio with edge-tts and rewrite lines_timed/segments/seconds."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

import edge_tts

VOICES = {
    "th": "th-TH-PremwadeeNeural",
    "en": "en-US-JennyNeural",
}
GAP_OPEN = 0.45
GAP_WITHIN = 0.30
GAP_PART = 0.55
LEAD_IN = 0.40


def collect_lines(ep: dict) -> list[dict]:
    out: list[dict] = []
    for line in ep["opening"]:
        out.append({"say": line["say"], "show": line["show"], "part": 0, "kind": "opening", "index": None})
    for i, item in enumerate(ep["news"]):
        for line in item["lines"]:
            out.append({"say": line["say"], "show": line["show"], "part": i + 1, "kind": "news", "index": i})
    closing_part = len(ep["news"]) + 1
    for line in ep["closing"]:
        out.append({"say": line["say"], "show": line["show"], "part": closing_part, "kind": "closing", "index": None})
    return out


def probe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(raw)


async def synth_line(text: str, voice: str, dest: Path, attempts: int = 5) -> None:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(dest))
            return
        except Exception as exc:  # edge-tts intermittently returns empty audio
            last_error = exc
            await asyncio.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"TTS failed for: {text!r}") from last_error


def write_silence(path: Path, seconds: float) -> None:
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            f"{seconds:.3f}",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def concat_mp3(parts: list[Path], dest: Path) -> None:
    listing = dest.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    listing.unlink(missing_ok=True)


def build_segments(timed: list[dict], total: float) -> list[dict]:
    segments: list[dict] = []
    for row in timed:
        key = (row["kind"], row["index"])
        if segments and (segments[-1]["kind"], segments[-1]["index"]) == key:
            segments[-1]["end"] = row["end"]
        else:
            segments.append(
                {
                    "kind": row["kind"],
                    "index": row["index"],
                    "start": row["start"],
                    "end": row["end"],
                }
            )
    if segments:
        segments[-1]["end"] = total
    return segments


async def build_episode(ep_path: Path, audio_path: Path, voice: str) -> dict:
    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    lines = collect_lines(ep)
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        piece_paths: list[Path] = []
        timed: list[dict] = []
        t = LEAD_IN

        lead = tmp_path / "lead.mp3"
        write_silence(lead, LEAD_IN)
        piece_paths.append(lead)

        prev_part = None
        for i, line in enumerate(lines):
            if i == 0:
                gap = 0.0
            elif line["part"] != prev_part:
                gap = GAP_PART
            else:
                gap = GAP_WITHIN
            if gap > 0:
                silence = tmp_path / f"gap_{i:02d}.mp3"
                write_silence(silence, gap)
                piece_paths.append(silence)
                t += gap

            clip = tmp_path / f"line_{i:02d}.mp3"
            await synth_line(line["say"], voice, clip)
            dur = probe_duration(clip)
            piece_paths.append(clip)
            timed.append(
                {
                    "start": round(t, 3),
                    "end": round(t + dur, 3),
                    "show": line["show"],
                    "part": line["part"],
                    "kind": line["kind"],
                    "index": line["index"],
                }
            )
            t += dur
            prev_part = line["part"]

        # short tail silence so the last caption does not cut off
        tail = tmp_path / "tail.mp3"
        write_silence(tail, GAP_OPEN)
        piece_paths.append(tail)
        t += GAP_OPEN

        concat_mp3(piece_paths, audio_path)
        total = round(probe_duration(audio_path), 3)

    lines_timed = [{"start": r["start"], "end": r["end"], "show": r["show"], "part": r["part"]} for r in timed]
    segments = build_segments(timed, total)
    ep["seconds"] = total
    ep["lines_timed"] = lines_timed
    ep["segments"] = segments
    ep_path.write_text(json.dumps(ep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"lang": ep["lang"], "seconds": total, "title": ep["title"], "lines": len(lines)}


def update_episodes_index(root: Path, date: str, results: dict[str, dict]) -> None:
    index_path = root / "episodes.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entry = None
    for row in index:
        if row.get("date") == date:
            entry = row
            break
    if entry is None:
        entry = {"date": date}
        index.insert(0, entry)
    for lang, info in results.items():
        entry[lang] = {"title": info["title"], "seconds": info["seconds"]}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--langs", default="th,en")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    results: dict[str, dict] = {}
    for lang in [x.strip() for x in args.langs.split(",") if x.strip()]:
        ep_path = args.root / "episodes" / f"{args.date}-{lang}.json"
        audio_path = args.root / "audio" / f"{args.date}-{lang}.mp3"
        voice = VOICES[lang]
        print(f"[{lang}] voice={voice} -> {audio_path}")
        info = await build_episode(ep_path, audio_path, voice)
        results[lang] = info
        print(f"[{lang}] {info['lines']} lines, {info['seconds']}s")

    update_episodes_index(args.root, args.date, results)
    print("updated episodes.json")


if __name__ == "__main__":
    asyncio.run(main())
