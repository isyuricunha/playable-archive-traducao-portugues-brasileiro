#!/usr/bin/env python3
"""Prepare a tested, isolated menu font candidate from original game assets.

The standalone command prepares an isolated candidate. The production build
calls patch() only after the translation is complete.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from native import Invalid, Serialized
from storage import durable, sha

ROOT = Path(__file__).resolve().parent.parent
FONT_SOURCE = ROOT / "translation-work/vendor/courier-prime/CourierPrime-Regular.ttf"
INPUT_SHA256 = "e0a57c03f72d20ebf4f763b466393a894bfe80ef31f547effc2a7a2444827ad7"
OUTPUT_SHA256 = "71594688ce4820b79037bc51bee62f2bd079ffefd441f26456d56b409377f274"
OLD_FONT_SHA256 = "6ee69c09d6bd841b3d4622ac5df12c85625a0b141fbdecad38c084cb23c810f4"
NEW_FONT_SHA256 = "72f793376f8e2841656bf21d77a5de010f2929bd6956a22ee848ad0c7eb978af"
FONT_PATH_ID = 133
FONT_OFFSET = 92
FONT_SIZE = 55734
REQUIRED_CHARS = "\u00c0\u00c1\u00c2\u00c3\u00c7\u00c9\u00ca\u00cd\u00d3\u00d4\u00d5\u00da\u00dc\u00e0\u00e1\u00e2\u00e3\u00e7\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00fc"


def sfnt_has_characters(font: bytes, characters: str) -> None:
    """Check a TrueType BMP format-4 cmap without a platform-specific runtime."""
    if len(font) < 12 or font[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        raise Invalid("FONT_FORMAT: invalid sfnt header")
    tables = struct.unpack_from(">H", font, 4)[0]
    if 12 + 16*tables > len(font):
        raise Invalid("FONT_FORMAT: truncated table directory")
    table_map = {}
    for i in range(tables):
        tag, _, offset, length = struct.unpack_from(">4sIII", font, 12+i*16)
        if offset + length > len(font):
            raise Invalid("FONT_FORMAT: table outside file")
        table_map[tag] = (offset, length)
    if b"cmap" not in table_map:
        raise Invalid("FONT_FORMAT: cmap missing")
    start, cmap_len = table_map[b"cmap"]
    if cmap_len < 4:
        raise Invalid("FONT_FORMAT: truncated cmap")
    subtable_count = struct.unpack_from(">H", font, start+2)[0]
    if 4+8*subtable_count > cmap_len:
        raise Invalid("FONT_FORMAT: truncated cmap directory")
    choices = []
    for i in range(subtable_count):
        platform, encoding, rel = struct.unpack_from(">HHI", font, start+4+i*8)
        if rel+4 > cmap_len:
            raise Invalid("FONT_FORMAT: cmap offset outside table")
        pos = start+rel
        if (platform == 0 or (platform == 3 and encoding in (1, 10))) and struct.unpack_from(">H", font, pos)[0] == 4:
            choices.append(pos)
    if not choices:
        raise Invalid("FONT_FORMAT: no supported Unicode BMP cmap")
    pos = choices[-1]
    length, seg_count_x2 = struct.unpack_from(">HH", font, pos+2)[0], struct.unpack_from(">H", font, pos+6)[0]
    end = pos+length
    count = seg_count_x2//2
    if end > start+cmap_len or not count or seg_count_x2 % 2 or 16+count*8 > length:
        raise Invalid("FONT_FORMAT: malformed cmap segments")
    ends = pos+14
    starts = ends+count*2+2
    deltas = starts+count*2
    ranges = deltas+count*2
    missing = []
    for ch in characters:
        cp = ord(ch)
        glyph = 0
        for i in range(count):
            finish = struct.unpack_from(">H", font, ends+i*2)[0]
            begin = struct.unpack_from(">H", font, starts+i*2)[0]
            if begin <= cp <= finish:
                delta = struct.unpack_from(">h", font, deltas+i*2)[0]
                ro = struct.unpack_from(">H", font, ranges+i*2)[0]
                if ro:
                    address = ranges+i*2+ro+2*(cp-begin)
                    if address+2 > end:
                        raise Invalid("FONT_FORMAT: glyph index outside cmap")
                    glyph = struct.unpack_from(">H", font, address)[0]
                    if glyph:
                        glyph = (glyph+delta) & 0xffff
                else:
                    glyph = (cp+delta) & 0xffff
                break
        if glyph == 0:
            missing.append(f"U+{cp:04X}")
    if missing:
        raise Invalid("FONT_MISSING_GLYPHS: "+", ".join(missing))


def patch(original: bytes, new_font: bytes) -> bytes:
    if sha(original) != INPUT_SHA256:
        raise Invalid("SOURCE_MISMATCH: unsupported sharedassets0.assets; obtain the verified original")
    if sha(new_font) != NEW_FONT_SHA256:
        raise Invalid("FONT_MISMATCH: restore the licensed Courier Prime font from the repository")
    sfnt_has_characters(new_font, REQUIRED_CHARS)
    asset = Serialized(original)
    font_obj = next((o for o in asset.objects if o.path_id == FONT_PATH_ID), None)
    if font_obj is None or font_obj.class_id != 128:
        raise Invalid("FONT_OBJECT_MISMATCH: expected Unity Font object 133")
    payload = asset.payload(font_obj)
    if len(payload) < FONT_OFFSET+FONT_SIZE or struct.unpack_from("<I", payload, FONT_OFFSET-4)[0] != FONT_SIZE:
        raise Invalid("FONT_OBJECT_MISMATCH: unexpected embedded font location")
    old_font = payload[FONT_OFFSET:FONT_OFFSET+FONT_SIZE]
    if sha(old_font) != OLD_FONT_SHA256:
        raise Invalid("FONT_OBJECT_MISMATCH: embedded source font differs")
    padding = (-FONT_SIZE) % 4
    if payload[FONT_OFFSET+FONT_SIZE:FONT_OFFSET+FONT_SIZE+padding] != b"\0"*padding:
        raise Invalid("FONT_OBJECT_MISMATCH: unknown font padding")
    new_payload = (payload[:FONT_OFFSET-4]+struct.pack("<I", len(new_font))+new_font
                   +b"\0"*((-len(new_font)) % 4)+payload[FONT_OFFSET+FONT_SIZE+padding:])
    output = asset.rewrite({FONT_PATH_ID: new_payload})
    reopened = Serialized(output)
    restored_obj = next(o for o in reopened.objects if o.path_id == FONT_PATH_ID)
    if reopened.payload(restored_obj) != new_payload:
        raise Invalid("FONT_REOPEN_FAILED: patched font object differs")
    if sha(output) != OUTPUT_SHA256:
        raise Invalid("FONT_OUTPUT_MISMATCH: output differs from the user-tested menu font")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="original sharedassets0.assets")
    parser.add_argument("--output", required=True, type=Path, help="candidate under translation-work/.state/menu-test")
    args = parser.parse_args()
    try:
        state_root = (ROOT/"translation-work/.state/menu-test").resolve()
        output = args.output.resolve()
        if not output.is_relative_to(state_root) or output == state_root:
            raise Invalid("UNSAFE_OUTPUT: output must be below translation-work/.state/menu-test")
        source = args.source.resolve()
        if source == output:
            raise Invalid("UNSAFE_OUTPUT: source and output must differ")
        data = source.read_bytes()
        result = patch(data, FONT_SOURCE.read_bytes())
        durable(output, result)
        if sha(output.read_bytes()) != sha(result):
            raise Invalid("OUTPUT_MISMATCH after write")
        print(json.dumps({"status": "prepared", "source_sha256": sha(data), "output": str(output),
                          "output_sha256": sha(result), "font_sha256": NEW_FONT_SHA256,
                          "unicode_characters_checked": len(REQUIRED_CHARS)}, indent=2))
        return 0
    except (Invalid, OSError, ValueError, struct.error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
