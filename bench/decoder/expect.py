#!/usr/bin/env python3
"""Hold the harness's output to what its test decoders must print (decisions/0014).

    python3 expect.py stub <run.out> <stimulus.bin>
    python3 expect.py format_test <run.out> <stimulus.bin>
    python3 expect.py manifest <stimulus directory> <linked stimulus.bin>
    python3 expect.py same-decoder "<image hash> <decoder hash>" "<image hash> <decoder hash>"

`stub` predicts every record that stub.c prints, from stimulus.bin alone. `format_test` compares
format_test.c's records with format_test.expected. Both also check every other line the program
prints: the stimulus header's values, the detection mode, the count, the number of records, and
the last line. They echo the lines that are not records, then print PASS, or FAIL and the first
difference.

`manifest` checks that the linked stimulus is the file its manifest.json names. `same-decoder`
checks that two stimuli gave two images but one decoder image (decisions/0014, section 1).

Independence, and its limit. This reads stimulus.bin through bench/stimulus/container.py, not
through the harness's reader, and sorts with Python's sort. The formatter's expected text was
written by hand from SPEC §3. But one person wrote both sides, so agreement shows they are
consistent, not that either is right.
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "stimulus"))
import container  # noqa: E402

KEYS = ("format", "chunks", "connections", "payload", "detection", "instret", "records")
LINE = re.compile(r"^(\w+) += (.*)$")


class Mismatch(Exception):
    pass


def need(ok, what):
    if not ok:
        raise Mismatch(what)


def stub_records(blob):
    """stub.c: one record per chunk, then one per connection at the end of input."""
    protocols, chunks = container.unpack(blob)
    at = [0] * len(protocols)
    records = []
    for conn, data in chunks:
        records.append((conn, f"{conn} {protocols[conn]} - stub at={at[conn]} "
                              f"bytes={data.hex()} len={len(data)}"))
        at[conn] += len(data)
    for conn, protocol in enumerate(protocols):
        records.append((conn, f"{conn} {protocol} - stub at={at[conn]} len=0"))
    records.sort(key=lambda r: r[0])  # stable, so each connection keeps its order
    return [line for _, line in records]


def format_test_records(_blob):
    with open(os.path.join(HERE, "format_test.expected")) as f:
        return f.read().splitlines()


def check_run(decoder, run_out, stimulus):
    with open(stimulus, "rb") as f:
        blob = f.read()
    _, version, _, chunks, connections, payload = container.HEADER.unpack_from(blob, 0)
    expected = {"stub": stub_records, "format_test": format_test_records}[decoder](blob)
    with open(run_out) as f:
        text = f.read()
    need(text.endswith("\n"), "the output ends with a newline")
    lines = text[:-1].split("\n")

    first = next((i for i, line in enumerate(lines) if line.startswith("format ")), None)
    need(first is not None, "the program printed its format line")
    for line in lines[:first]:  # the Makefile's lines: what ran
        print(line)
    out = lines[first:]

    values = {}
    for i, key in enumerate(KEYS):
        m = LINE.match(out[i]) if i < len(out) else None
        need(m and m.group(1) == key, f"line {i + 1} of the program's output is `{key} = …`")
        values[key] = m.group(2)
        print(out[i])
    for key, want in (("format", version), ("chunks", chunks), ("connections", connections),
                      ("payload", payload), ("detection", "none"), ("records", len(expected))):
        need(values[key] == str(want), f"{key} = {want}, not {values[key]}")
    need(re.fullmatch(r"[1-9][0-9]*", values["instret"]), "instret is a positive decimal count")

    records = out[len(KEYS):len(KEYS) + len(expected)]
    for n, (got, want) in enumerate(zip(records, expected), 1):
        need(got == want, f"record {n} differs:\n  got  {got}\n  want {want}")
    need(len(records) == len(expected), f"{len(expected)} records, not {len(records)}")
    rest = out[len(KEYS) + len(expected):]
    m = LINE.match(rest[0]) if len(rest) == 1 else None
    need(m and m.group(1) == "end" and m.group(2) == str(len(expected)),
         f"the last line is `end = {len(expected)}`, and nothing follows it")
    print(rest[0])
    print(f"expect: PASS. {len(expected)} records from {decoder}.c match, in canonical order.")


def manifest(directory, linked):
    with open(os.path.join(directory, "manifest.json")) as f:
        want = json.load(f)["outputs"]["stimulus.bin"]["sha256"]
    with open(linked, "rb") as f:
        got = hashlib.sha256(f.read()).hexdigest()
    need(got == want, f"the linked stimulus is sha256:{got}, but its manifest.json says sha256:{want}")
    print(f"manifest = matches {os.path.join(directory, 'manifest.json')}")


def same_decoder(one, two):
    image_1, decoder_1 = one.split()
    image_2, decoder_2 = two.split()
    need(image_1 != image_2, "the two stimuli gave one image, so they were one stimulus")
    need(decoder_1 == decoder_2, "the decoder's image changed with the stimulus")
    print(f"decoder: PASS. Two stimuli gave two images and one decoder image, sha256:{decoder_1}.")


def main(argv):
    try:
        if len(argv) == 4 and argv[1] in ("stub", "format_test"):
            check_run(argv[1], argv[2], argv[3])
        elif len(argv) == 4 and argv[1] == "manifest":
            manifest(argv[2], argv[3])
        elif len(argv) == 4 and argv[1] == "same-decoder":
            same_decoder(argv[2], argv[3])
        else:
            print(__doc__.split("\n\n")[1])
            return 2
    except Mismatch as e:
        print(f"expect: FAIL. {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
