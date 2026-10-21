#!/usr/bin/env python3
"""Break the harness on purpose, one fault at a time, and check that something catches each fault.

    python3 mutate.py        (make mutate)

A check that has never failed proves nothing. Each case below changes one source file, or links
one corrupted stimulus, and must end with a non-zero exit: a failed `make expect`, a failed
same-decoder check, or a stimulus that the harness refuses. Every source file is restored after its
case, whatever happens. Each run has a time limit, so a fault that hangs Spike is reported as
a hang instead of stopping this script.

Needs the coverage stimulus for seeds 1 and 2: run `make check` first.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
STIMULUS = os.path.join(os.path.dirname(HERE), "stimulus")
sys.path.insert(0, STIMULUS)
import container  # noqa: E402

LIMIT = 180  # seconds for one build and run. A clean run takes about 2.

SOURCE_FAULTS = [
    # (what is broken, file, text, its replacement, check)
    ("a negative number loses its sign", "output.c", "        out_char('-');\n", "",
     "format_test"),
    ("a u64 loses its top digit", "output.c", "    int i = 19;\n", "    int i = 18;\n",
     "format_test"),
    ("an odd hex value keeps its first nibble", "output.c", "i = nibbles & 1, end", "i = 0, end",
     "format_test"),
    ("fields are not sorted by name", "harness.c", "    for (uint32_t i = 1; i < n; i++) {\n",
     "    for (uint32_t i = n; i < n; i++) {\n", "stub"),
    ("records of one connection change order", "harness.c",
     "        index[count[r[0] >> 16]++] = (uint32_t)(r - base);\n",
     "        index[count[r[0] >> 16]++] = (uint32_t)(r - base);\n"
     "    for (uint32_t i = 0; i + 1 < total; i += 2) {\n"
     "        uint32_t t = index[i];\n"
     "        index[i] = index[i + 1];\n"
     "        index[i + 1] = t;\n"
     "    }\n", "stub"),
    ("the chunk walk ignores padding", "harness.c", "        p += 4 + ((n + 3) & ~3u);",
     "        p += 4 + n;", "stub"),
    ("every chunk takes the GT06 path", "stub.c", "    if (conns[conn].protocol == PROTO_GT06)",
     "    if (1)", "stub"),
    ("the last line is missing", "harness.c", "    put_line(\"end\", total);\n", "", "stub"),
    ("the last buffer is never written", "harness.c",
     "    put_line(\"end\", total);\n    out_flush();\n",
     "    put_line(\"end\", total);\n", "stub"),
    ("the stimulus moves the decoder", "link.ld",
     "  /* tohost/fromhost live here",
     "  .stimulus ALIGN(16) : { KEEP(*(.stimulus)) }\n  /* tohost/fromhost live here",
     "same-decoder"),
]


def run(args):
    """(exit status, the last line that says why), or a hang."""
    try:
        r = subprocess.run(args, cwd=HERE, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", "spike --isa=rv32im build/"])
        return None, f"HANG: no result after {LIMIT} s"
    lines = (r.stdout + r.stderr).splitlines()
    why = next((line for line in lines if "FAIL" in line or "refused" in line or "trap" in line),
               lines[-1] if lines else "")
    return r.returncode, why


def hashes(stim):
    """`<image hash> <decoder hash>`, or nothing if the build fails."""
    try:
        r = subprocess.run(["make", "-s", "--no-print-directory", "hashes", f"STIM={stim}"],
                           cwd=HERE, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def source_fault(name, path, old, new, check):
    path = os.path.join(HERE, path)
    with open(path) as f:
        original = f.read()
    assert original.count(old) == 1, f"{name}: the text to change is not in {path} once"
    changed = original.replace(old, new)
    if name == "the stimulus moves the decoder":  # it moves, so take it out of its old place
        tail = "\n  .stimulus ALIGN(16) : { KEEP(*(.stimulus)) }\n}"
        assert changed.count(tail) == 1
        changed = changed.replace(tail, "\n}")
    try:
        with open(path, "w") as f:
            f.write(changed)
        if check == "same-decoder":
            one = hashes("../stimulus/build/coverage-1")
            two = hashes("../stimulus/build/coverage-2")
            return run(["python3", "expect.py", "same-decoder", one, two])
        return run(["make", "expect", f"DECODER={check}"])
    finally:
        with open(path, "w") as f:
            f.write(original)


def stimulus_faults(tmp):
    """A 13-connection stimulus, so the table has padding, then one corruption at a time. Each
    corrupted file gets a manifest.json that names it, so only the harness's own check can stop
    it."""
    with open(os.path.join(STIMULUS, "params", "coverage.json")) as f:
        params = json.load(f)
    params["connections"] = 13
    with open(os.path.join(tmp, "params.json"), "w") as f:
        json.dump(params, f)
    base = os.path.join(tmp, "thirteen")
    subprocess.run(["python3", os.path.join(STIMULUS, "generate.py"), "--params",
                    os.path.join(tmp, "params.json"), "--seed", "1", "--out", base],
                   check=True, capture_output=True)
    with open(os.path.join(base, "stimulus.bin"), "rb") as f:
        blob = f.read()
    protocols, chunks = container.unpack(blob)
    first = 20 + len(protocols) + -len(protocols) % 4
    offset, chunk_pad = first, None
    for _, data in chunks:
        if len(data) % 4 and chunk_pad is None:
            chunk_pad = offset + 4 + len(data)
        offset += 4 + len(data) + -len(data) % 4

    def byte(at, value):
        return lambda b: b.__setitem__(at, value)

    def payload_plus_one(b):
        b[16:20] = (int.from_bytes(b[16:20], "little") + 1).to_bytes(4, "little")

    cases = [("version 1", byte(4, 1)), ("a protocol code of 3", byte(20, 3)),
             ("non-zero padding after the table", byte(20 + len(protocols), 1)),
             ("non-zero padding after a chunk", byte(chunk_pad, 1)),
             ("a chunk for a connection that does not exist", byte(first + 2, len(protocols))),
             ("a payload total one too high", payload_plus_one)]
    for name, edit in cases:
        d = os.path.join(tmp, name.replace(" ", "-"))
        shutil.copytree(base, d)
        b = bytearray(blob)
        edit(b)
        with open(os.path.join(d, "stimulus.bin"), "wb") as f:
            f.write(b)
        with open(os.path.join(d, "manifest.json")) as f:
            m = json.load(f)
        m["outputs"]["stimulus.bin"]["sha256"] = hashlib.sha256(b).hexdigest()
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump(m, f)
        yield "stimulus: " + name, run(["make", "run", f"STIM={d}"])


def main():
    results = []
    for name, path, old, new, check in SOURCE_FAULTS:
        results.append((name, source_fault(name, path, old, new, check)))
        print(results[-1][0], "->", results[-1][1][1], flush=True)
    with tempfile.TemporaryDirectory(prefix="decoder-mutate-") as tmp:
        for name, result in stimulus_faults(tmp):
            results.append((name, result))
            print(name, "->", result[1], flush=True)
    caught = [name for name, (status, _) in results if status]
    print()
    for name, (status, why) in results:
        print(f"{'caught' if status else 'MISSED'}  {name}")
    print(f"mutate: {len(caught)} of {len(results)} faults caught.")
    return 0 if len(caught) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
