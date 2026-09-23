#!/usr/bin/env python3
"""Move the source recording to the Trash once the cut file has replaced it.

Why this exists: after a run, the source sits in `素材/` at several times the
size of the cut file that everything downstream is bound to — the transcript,
the subtitles, the note. Once the cut file is verified, the source is weight.

Why the Trash and not `unlink`: the one thing no automatic check can catch is
the resolution decision (see SKILL.md, first step) — it needs human eyes, and
finding out later that the whiteboard text is mushy means re-rendering from the
source. The Trash keeps that possible for as long as it is not emptied, at the
cost of not freeing the disk until then.

Every check below is measured against this material's own record rather than an
absolute number, and any one of them failing means the source stays put. The
refusal is the point: a source moved on a bad cut is unrecoverable once the
Trash is emptied.

    python3 trash_source.py <源文件> <剪后文件> <剪辑表.json>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# What the product writes into a file it rendered. Travels with the bytes, so a
# renamed or moved file is still recognised.
CUT_FILE_MARK = "fluentflow_debreath=1"

# How far the cut file's real duration may sit from the length the cut list says
# it should be. Wider of the two: a couple of seconds, or 1% of the source.
DURATION_TOLERANCE_SECONDS = 2.0
DURATION_TOLERANCE_RATIO = 0.01


class Refused(Exception):
    """A reason the source must stay where it is, in a sentence."""


def _probe(media: Path, entries: list[str]) -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", *entries, "-of", "default=nw=1:nk=1", str(media)],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        raise Refused(f"ffprobe 读不了 {media.name}：{out.stderr.strip() or '未知错误'}")
    return out.stdout.strip()


def _duration(media: Path) -> float:
    raw = _probe(media, ["-show_entries", "format=duration"])
    try:
        return float(raw.splitlines()[0])
    except (ValueError, IndexError):
        raise Refused(f"量不出 {media.name} 的时长，核不了剪后文件是否完整")


def _stream_types(media: Path) -> list[str]:
    raw = _probe(media, ["-show_entries", "stream=codec_type"])
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _check_cut_is_ours(cut: Path) -> str:
    """Whether this file is a cut of ours, and how certain that is."""
    tags = _probe(cut, ["-show_entries", "format_tags=comment"])
    if CUT_FILE_MARK in tags:
        return "文件里有 FluentFlow 的剪辑标记"
    if "_debreath" in cut.stem:
        return f"靠文件名判断（{cut.name}），文件里没有剪辑标记"
    raise Refused(
        f"{cut.name} 既没有剪辑标记、名字里也没有 _debreath，"
        "认不出它是这条流程剪出来的，不动源文件"
    )


def _check_cut_list(cut_list: Path, source: Path, cut: Path) -> dict:
    """Tie source, cut list and cut file together, and read the spot check."""
    try:
        plan = json.loads(cut_list.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Refused(f"读不了剪辑表 {cut_list.name}：{exc}")

    # The spot check is the only thing that catches cuts sitting close to the
    # speech, and it is the case where the source is the only way to hear what
    # was shaved off.
    separation = plan.get("level_separation") or {}
    if separation.get("measured") and not separation.get("separated", True):
        raise Refused(
            "剪辑表里的抽查说剪掉的部分只比紧邻的说话声低一点点"
            f"（最窄 {separation.get('narrowest_db')}dB），这份剪后文件可能吃掉了字，源文件留着"
        )
    if plan.get("warnings"):
        raise Refused(
            "剪辑表带着警告，先看警告再决定：\n  - " + "\n  - ".join(plan["warnings"])
        )

    planned_source = float(plan.get("source_duration_seconds") or 0)
    planned_kept = float(plan.get("kept_seconds") or 0)
    if planned_source <= 0 or planned_kept <= 0:
        raise Refused(f"剪辑表 {cut_list.name} 里没有时长记录，核不了这三个文件是一组的")

    tolerance = max(DURATION_TOLERANCE_SECONDS, planned_source * DURATION_TOLERANCE_RATIO)

    source_duration = _duration(source)
    if abs(source_duration - planned_source) > tolerance:
        raise Refused(
            f"源文件 {source_duration:.1f}s 和剪辑表记的 {planned_source:.1f}s 不一致，"
            "这份剪辑表不是从这个源文件算出来的"
        )

    cut_duration = _duration(cut)
    if abs(cut_duration - planned_kept) > tolerance:
        raise Refused(
            f"剪后文件 {cut_duration:.1f}s 和剪辑表算的 {planned_kept:.1f}s 差得多，"
            "渲染可能被截断了"
        )
    return {
        "source_duration": source_duration,
        "cut_duration": cut_duration,
        "removed_percent": plan.get("removed_percent"),
    }


def _check_streams(source: Path, cut: Path) -> None:
    """The cut must carry what the source carried; a missing stream is silent."""
    source_types = _stream_types(source)
    cut_types = _stream_types(cut)
    if "audio" not in cut_types:
        raise Refused(f"剪后文件 {cut.name} 里没有音轨")
    if "video" in source_types and "video" not in cut_types:
        raise Refused(f"源文件有画面，剪后文件 {cut.name} 只有声音")


def _to_trash(path: Path) -> str:
    """Finder's own delete, so the file keeps its Put Back."""
    script = f'tell application "Finder" to delete POSIX file "{path}"'
    done = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if done.returncode == 0:
        return "已放进回收站，Finder 里可以「放回原处」"
    # Automating Finder can be refused by the OS. Moving the file ourselves is
    # still recoverable, it just loses Put Back — say so rather than pretend.
    trash = Path.home() / ".Trash"
    target = trash / path.name
    stem, suffix, n = target.stem, target.suffix, 1
    while target.exists():
        target = trash / f"{stem} {n}{suffix}"
        n += 1
    path.rename(target)
    return f"已移到 {target}（Finder 自动化被拒，所以没有「放回原处」，手动拖回来即可）"


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    source, cut, cut_list = (Path(a).expanduser() for a in sys.argv[1:4])

    try:
        for path in (source, cut, cut_list):
            if not path.is_file():
                raise Refused(f"找不到 {path}")
        how = _check_cut_is_ours(cut)
        _check_streams(source, cut)
        measured = _check_cut_list(cut_list, source, cut)
    except Refused as exc:
        print(f"没有动源文件：{exc}")
        return 1

    freed = source.stat().st_size / 1024 / 1024
    kept = cut.stat().st_size / 1024 / 1024
    where = _to_trash(source)
    print(
        f"源文件 {source.name} {where}。\n"
        f"核过：{how}；源 {measured['source_duration']:.1f}s → 剪后 {measured['cut_duration']:.1f}s"
        f"（剪掉 {measured['removed_percent']}%），音轨画面都在。\n"
        f"腾出 {freed:.0f}MB，留下的剪后文件 {kept:.0f}MB。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
