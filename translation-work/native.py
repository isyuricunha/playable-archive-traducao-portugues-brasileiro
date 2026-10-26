"""Strict Unity 6000 serialized-file v22 adapter. No native dependencies.

Only TextAsset objects are interpreted. Other object payloads and metadata are
opaque and preserved. Format research: docs/formato-localizacao.md.
"""
from __future__ import annotations

import collections
import dataclasses
import re
import struct
from urllib.parse import quote

DEPLOY = "Playable Archive_Data/resources.assets"
HEADER = "KEY;English;French;Italian;German;Spanish;Chinese;Japanese"
LANGUAGES = HEADER.split(";")[1:]


class Invalid(ValueError):
    pass


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def take(self, n):
        if n < 0 or self.pos + n > len(self.data):
            raise Invalid(f"Malformed serialized data at {self.pos}, length {n}")
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def number(self, fmt):
        return struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))[0]

    def align(self, n=4):
        self.take((-self.pos) % n)

    def zstring(self):
        end = self.data.find(b"\0", self.pos)
        if end < 0:
            raise Invalid("Unterminated metadata string")
        return self.take(end-self.pos+1)[:-1].decode("utf-8")

    def string(self):
        return self.take(self.number("i")).decode("utf-8")


@dataclasses.dataclass
class Object:
    path_id: int
    offset: int
    size: int
    class_id: int
    entry: int


class Serialized:
    def __init__(self, data):
        self.data = data
        if len(data) < 48 or struct.unpack_from(">I", data, 8)[0] != 22:
            raise Invalid("UNSUPPORTED_FORMAT: expected Unity serialized file v22")
        self.metadata_size, size, self.data_offset = struct.unpack_from(">IQQ", data, 20)
        if size != len(data) or data[16:20] != b"\0\0\0\0":
            raise Invalid("Invalid size, endian or reserved bytes")
        if not 48 < 48+self.metadata_size <= self.data_offset <= size:
            raise Invalid("Invalid metadata/data boundaries")
        r = Reader(data, 48)
        self.unity = r.zstring()
        if not self.unity.startswith("6000."):
            raise Invalid(f"UNSUPPORTED_ENGINE: {self.unity}; adapter supports Unity 6000")
        self.platform = r.number("i")
        if self.platform != 19:
            raise Invalid(f"UNSUPPORTED_PLATFORM: {self.platform}; expected Windows64 (19)")
        trees = r.number("B")
        if trees not in (0, 1):
            raise Invalid("Invalid type tree flag")
        types = []
        count = r.number("i")
        if not 0 < count < 100000:
            raise Invalid("Invalid type count")
        for _ in range(count):
            cls = r.number("i")
            r.take(3)  # stripped + script type index
            if cls == 114:
                r.take(16)
            r.take(16)  # old type hash
            if trees:
                nodes, strings = r.number("i"), r.number("i")
                if nodes < 0 or strings < 0:
                    raise Invalid("Invalid type tree size")
                r.take(nodes*32 + strings)
                r.take(r.number("i")*4)  # type dependencies
            types.append(cls)
        self.objects = []
        count = r.number("i")
        if not 0 < count < 1000000:
            raise Invalid("Invalid object count")
        ids = set()
        for _ in range(count):
            r.align()
            entry = r.pos
            pid, offset, length, tid = (r.number("q"), r.number("q"),
                                        r.number("I"), r.number("i"))
            if pid in ids or not 0 <= tid < len(types):
                raise Invalid("Duplicate object ID or invalid type index")
            ids.add(pid)
            if offset < 0 or offset+length > size-self.data_offset:
                raise Invalid("Object outside data section")
            self.objects.append(Object(pid, offset+self.data_offset, length, types[tid], entry))
        if r.pos > 48+self.metadata_size:
            raise Invalid("Object table exceeds metadata")
        end = self.data_offset
        for obj in sorted(self.objects, key=lambda o: o.offset):
            if obj.offset < end:
                raise Invalid("Overlapping object payloads")
            end = obj.offset+obj.size

    def payload(self, obj):
        return self.data[obj.offset:obj.offset+obj.size]

    def text_assets(self):
        result = {}
        for obj in self.objects:
            if obj.class_id != 49:
                continue
            raw = self.payload(obj)
            r = Reader(raw)
            name = r.string()
            r.align()
            length_pos = r.pos
            text = r.take(r.number("i"))
            suffix = raw[r.pos:]
            if suffix != b"\0"*((-r.pos) % 4):
                raise Invalid(f"Unknown TextAsset trailing data: {name}")
            if name in result:
                raise Invalid(f"Duplicate TextAsset name: {name}")
            result[name] = {"object": obj, "bytes": text,
                            "prefix": raw[:length_pos], "suffix": suffix}
        return result

    def rewrite(self, replacements):
        """Repack payloads at original 8-byte alignment, retaining opaque gaps."""
        known = {o.path_id for o in self.objects}
        if set(replacements)-known:
            raise Invalid("Unknown replacement object")
        replacements = {pid: value for pid, value in replacements.items()
                        if value != self.payload(next(o for o in self.objects if o.path_id == pid))}
        if not replacements:
            return self.data
        out = bytearray(self.data[:self.data_offset])
        cursor = self.data_offset
        for obj in sorted(self.objects, key=lambda o: o.offset):
            out.extend(self.data[cursor:obj.offset])
            out.extend(b"\0"*((obj.offset-len(out)) % 8))
            offset = len(out)
            payload = replacements.get(obj.path_id, self.payload(obj))
            out.extend(payload)
            struct.pack_into("<qI", out, obj.entry+8, offset-self.data_offset, len(payload))
            cursor = obj.offset+obj.size
        out.extend(self.data[cursor:])
        struct.pack_into(">Q", out, 24, len(out))
        rebuilt = bytes(out)
        check = Serialized(rebuilt)
        expected = {o.path_id: replacements.get(o.path_id, self.payload(o)) for o in self.objects}
        if any(check.payload(o) != expected.pop(o.path_id) for o in check.objects) or expected:
            raise Invalid("Rebuilt object inventory differs")
        return rebuilt


def tables(data):
    serialized = Serialized(data)
    result = {}
    global_keys = set()
    for name, asset in serialized.text_assets().items():
        raw = asset["bytes"]
        if not raw.startswith(HEADER.encode()):
            continue
        text = raw.decode("utf-8")
        lines = text.splitlines(keepends=True)
        if lines[0].rstrip("\r\n") != HEADER:
            raise Invalid(f"Invalid language header: {name}")
        rows = []
        for line_no, line in enumerate(lines[1:], 1):
            if not line.strip():
                continue
            columns = line.rstrip("\r\n").split(";")
            if len(columns) != 8 or not columns[0].strip() or not columns[1].strip():
                raise Invalid(f"Invalid row {name}:{line_no}; expected 8 nonquoted columns and English")
            key = columns[0].strip()
            if key in global_keys:
                raise Invalid(f"Duplicate global localization key: {key}")
            global_keys.add(key)
            rows.append((line_no, columns))
        result[name] = {**asset, "lines": lines, "rows": rows}
    if not result:
        raise Invalid("No Playable Archive localization tables found")
    return serialized, result


def extract(data):
    serialized, found = tables(data)
    records = []
    for name in sorted(found):
        asset = found[name]
        for line_no, columns in asset["rows"]:
            key = columns[0].strip()
            records.append({"id": f"{DEPLOY}#{quote(name, safe='')}/{quote(key, safe='')}",
                            "source_file": DEPLOY, "table": name, "key": key,
                            "row": line_no, "path_id": asset["object"].path_id,
                            "EN": columns[1], "original_languages": dict(zip(LANGUAGES[1:], columns[2:])),
                            "PTBR": ""})
    return records, {"unity": serialized.unity, "platform": serialized.platform,
                     "tables": {name: len(asset["rows"]) for name, asset in sorted(found.items())},
                     "objects": len(serialized.objects)}


TOKEN = re.compile(r"%[?+]|\{\d+(?::[^{}]*)?\}|%(?:\d+\$)?[sdif]|<[^<>]+>")


def markup_errors(text):
    stack, errors = [], []
    for tag in re.findall(r"<[^<>]+>", text):
        m = re.fullmatch(r"<(/?)([a-zA-Z]+)(?:=[^<>]+)?\s*/?>", tag)
        if not m:
            errors.append(tag)
            continue
        closing, name = m.groups()
        name = name.lower()
        if name in {"br", "sprite", "space", "page", "pos", "quad"} or tag.endswith("/>"):
            continue
        if closing:
            if not stack or stack.pop() != name:
                errors.append(tag)
        else:
            stack.append(name)
    return errors + stack


def validate_text(source, target):
    if not isinstance(target, str) or not target.strip():
        raise Invalid("PTBR must be a nonempty string")
    if any(c in target for c in ";\r\n\x00") or any(ord(c) < 32 for c in target):
        raise Invalid("Literal semicolon/newline/control character breaks the game's Split(';') parser; use <br>")
    if collections.Counter(TOKEN.findall(source)) != collections.Counter(TOKEN.findall(target)):
        raise Invalid("Protected placeholders/tags differ from English")
    # Several original entries have malformed tags. Preserve their exact tag
    # stream rather than inventing an undocumented correction to source markup.
    if markup_errors(target):
        source_tags = re.findall(r"<[^<>]+>", source)
        if not markup_errors(source) or source_tags != re.findall(r"<[^<>]+>", target):
            raise Invalid("Unbalanced or reordered markup")
    target.encode("utf-8", errors="strict")


def build(data, records):
    serialized, found = tables(data)
    by_key = {(r["table"], r["key"]): r for r in records}
    replacements = {}
    for name, asset in found.items():
        lines = list(asset["lines"])
        for line_no, columns in asset["rows"]:
            record = by_key.pop((name, columns[0].strip()))
            if columns[1] != record["EN"]:
                raise Invalid("Build source differs from record")
            validate_text(record["EN"], record["PTBR"])
            ending = lines[line_no][len(lines[line_no].rstrip("\r\n")):]
            translated = list(columns)
            translated[1] = record["PTBR"]
            lines[line_no] = ";".join(translated)+ending
        script = "".join(lines).encode("utf-8")
        payload = asset["prefix"]+struct.pack("<i", len(script))+script
        replacements[asset["object"].path_id] = payload+b"\0"*(-len(payload) % 4)
    if by_key:
        raise Invalid("Unknown records at build")
    output = serialized.rewrite(replacements)
    reopened, _ = extract(output)
    expected = {r["id"]: r["PTBR"] for r in records}
    if {r["id"]: r["EN"] for r in reopened} != expected:
        raise Invalid("Reopened build strings do not match PTBR")
    return output


def fixture(text="Fixture %?", count=1):
    """Valid tiny v22 file, not arbitrary bytes labeled as a Unity fixture."""
    script = HEADER+"\n"+"".join(f"key{i};{text};;;;;;\n" for i in range(count))
    name = b"Fixture"
    payload = struct.pack("<i", len(name))+name
    payload += b"\0"*(-len(payload) % 4)
    payload += struct.pack("<i", len(script.encode()))+script.encode()
    payload += b"\0"*(-len(payload) % 4)
    metadata = bytearray(b"6000.0.72f1\0"+struct.pack("<iBi", 19, 0, 1))
    metadata.extend(struct.pack("<iBh", 49, 0, -1)+b"\0"*16)
    metadata.extend(struct.pack("<i", 1))
    metadata.extend(b"\0"*(-(48+len(metadata)) % 4))
    metadata.extend(struct.pack("<qqIi", 1, 0, len(payload), 0))
    metadata.extend(struct.pack("<iii", 0, 0, 0)+b"\0")
    data_offset = (48+len(metadata)+15)//16*16
    header = struct.pack(">IIII", 0, 0, 22, 0)+b"\0"*4
    header += struct.pack(">IQQQ", len(metadata), data_offset+len(payload), data_offset, 0)
    return header+metadata+b"\0"*(data_offset-48-len(metadata))+payload
