#!/usr/bin/env python3
"""Generate a stimulus: the decoder's input, what the generator intended, and a manifest.

    python3 generate.py --params params/coverage.json --seed 1 --out build/coverage-1

Writes three files to --out:

    stimulus.bin    the chunks, in delivery order (container.py)
    intent.jsonl    one line per connection, frame and garbage run, in each connection's byte order
                    with its offset. This is the ground truth the reference decoder's output will be
                    checked against, and it is not that output (decisions/0004's order: the
                    reference decoder produces the expected output).
    manifest.json   seed, parameters and rules (all assumptions), the generator's identity, output
                    hashes, and what the run actually contains

A stimulus is versioned as generator + parameters + seed, and never committed (bench/SPEC.md §8).
Run check.py on the output before using it.
"""

import argparse
import bisect
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter

import container
import traffic
from prng import SplitMix64

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ("prng.py", "common.py", "gt06.py", "jt808.py", "traffic.py", "container.py", "generate.py")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def generator_identity():
    """What produced this stimulus: each source file's hash, and the commit if there is one."""
    ident = {"sources": {}}
    for name in SOURCES:
        with open(os.path.join(HERE, name), "rb") as f:
            ident["sources"][name] = sha256(f.read())
    try:
        git = ["git", "-C", HERE]
        ident["commit"] = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True,
                                         text=True, check=True).stdout.strip()
        changed = subprocess.run(git + ["status", "--porcelain", "--", "."], capture_output=True,
                                 text=True, check=True).stdout.strip()
        ident["tree"] = "clean" if not changed else "UNCOMMITTED CHANGES in bench/stimulus"
    except (OSError, subprocess.CalledProcessError):
        ident["commit"], ident["tree"] = "unknown", "not a git checkout"
    return ident


def intent_lines(conns):
    """Every connection, then its segments with their offsets, in the connection's byte order."""
    for conn in conns:
        yield conn.record()
        offset = 0
        for seg in conn.segments:
            yield dict(seg.record, offset=offset, length=len(seg.data))
            offset += len(seg.data)


def realized(conns, chunks):
    """What the run contains, counted. Parameters are rates; these are the outcomes."""
    c = Counter()
    frames_by_type, faults, framing = Counter(), Counter(), Counter()
    per_conn = []
    ends, offset = {}, Counter()  # each connection's chunk boundaries, as stream offsets
    for conn, data in chunks:
        offset[conn] += len(data)
        ends.setdefault(conn, []).append(offset[conn])
    split = 0
    for conn in conns:
        c[f"connections.{conn.protocol}"] += 1
        if conn.protocol == "jt808":
            c[f"connections.jt808.delimiter_{conn.delimiter:02x}"] += 1
            c[f"connections.jt808.version_{conn.version}"] += 1
        n, pos = 0, 0
        for seg in conn.segments:
            r = seg.record
            c[f"bytes.{conn.protocol}.{seg.kind}"] += len(seg.data)
            if seg.kind == "garbage":
                c["garbage.runs"] += 1
                c["garbage.bytes"] += len(seg.data)
            else:
                n += 1
                frames_by_type[f"{conn.protocol} {r['type']}"] += 1
                framing[r["framing"]] += 1
                faults[r["fault"] or "none"] += 1
                c["jt808.escape_pairs"] += r.get("escapes", 0)
                if r["type"] == "0x0704":
                    c["jt808.batch_records"] += len(r["fields"]["records"])
                b = ends.get(conn.conn, [])
                k = bisect.bisect_right(b, pos)  # the first boundary after the frame starts
                split += k < len(b) and b[k] < pos + len(seg.data)
            pos += len(seg.data)
        per_conn.append(n)
    sizes = [len(d) for _, d in chunks]
    return {
        "counts": dict(sorted(c.items())),
        "frames": sum(per_conn),
        "frames_by_type": dict(sorted(frames_by_type.items())),
        "frames_by_framing": dict(sorted(framing.items())),
        "frames_by_fault": dict(sorted(faults.items())),
        "frames_per_connection": {"min": min(per_conn), "max": max(per_conn)},
        "frames_split_across_chunks": split,
        "chunks": {"count": len(chunks), "min_bytes": min(sizes), "max_bytes": max(sizes),
                   "payload_bytes": sum(sizes)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--params", required=True, help="parameter file (JSON)")
    ap.add_argument("--seed", required=True, type=int, help="SplitMix64 seed, 0 to 2**64-1")
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args(argv)

    with open(args.params) as f:
        params = json.load(f)
    try:
        conns, chunks = traffic.generate(params, SplitMix64(args.seed))
    except traffic.ParamError as e:
        print(f"{args.params}: {e}", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    blob = container.pack(chunks, len(conns))
    intent = "".join(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n"
                     for line in intent_lines(conns)).encode()
    stats = realized(conns, chunks)
    manifest = {
        "manifest": "bench/stimulus, format 1",
        "seed": args.seed,
        "params_file": os.path.relpath(os.path.abspath(args.params), os.path.dirname(HERE)),
        "params": params,
        "status_of_every_parameter": "assumption: bench/SPEC.md lists each as unset, with no source",
        "rules": traffic.RULES,
        "generator": generator_identity(),
        "outputs": {"stimulus.bin": {"bytes": len(blob), "sha256": sha256(blob)},
                    "intent.jsonl": {"bytes": len(intent), "sha256": sha256(intent)}},
        "realized": stats,
    }
    with open(os.path.join(args.out, "stimulus.bin"), "wb") as f:
        f.write(blob)
    with open(os.path.join(args.out, "intent.jsonl"), "wb") as f:
        f.write(intent)
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"stimulus  sha256:{sha256(blob)}  {len(blob)} bytes, {len(chunks)} chunks")
    print(f"intent    sha256:{sha256(intent)}")
    print(f"frames    {stats['frames']} on {len(conns)} connections, "
          f"{stats['frames_split_across_chunks']} split across chunks")
    for key in ("frames_by_type", "frames_by_framing", "frames_by_fault"):
        print(f"{key[10:]:9} " + ", ".join(f"{k} {v}" for k, v in stats[key].items()))
    counts = stats["counts"]
    print(f"garbage   {counts.get('garbage.runs', 0)} runs, {counts.get('garbage.bytes', 0)} bytes")
    print(f"escapes   {counts.get('jt808.escape_pairs', 0)} pairs in "
          f"{counts.get('bytes.jt808.frame', 0)} bytes of JT808 frames (rule R6)")
    print(f"written   {args.out}/  (stimulus.bin, intent.jsonl, manifest.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
