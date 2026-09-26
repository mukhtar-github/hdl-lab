#!/usr/bin/env python3
"""Build the CRC Byte Anatomy page from Spike's commit log.

    make -C bench/rv32 anatomy
        -> build/crc-byte-anatomy.html              the page, as published (an Artifact fragment)
        -> build/crc-byte-anatomy.standalone.html   the same page, wrapped to open in a browser

Three builds of crc_itu_ref.c compute the same byte of CRC-16/X-25 in different ways. For each one,
this builds it with the Makefile, runs it under Spike with --log-commits, and takes the first byte
of the reference CRC: from the first `lbu` (which must load the frame's first byte) to the next.
Every instruction in that window gets a role and a plain-English note, and the page is written from
crc_anatomy.html.

The notes describe the instruction sequences that GCC 16.2.0 emits for today's source. If a build
executes a different sequence, this script stops and names the first instruction that differs,
because its notes would otherwise describe code that is not there. The numbers inside the notes
come from Spike's log, not from this file.

Needs Spike built with --enable-commitlog (see README.md).
"""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ABI = ("zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 "
       "a6 a7 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6").split()
BYTES = 12012  # 1001 CRCs of a 12-byte frame: crc_itu_ref.c's declared work

# ---------------------------------------------------------------------------
# What each build is expected to execute for one byte, with a role and a note
# for every instruction. {v} is the value the instruction wrote (low 16 bits),
# {b} its low 8 bits, {mem} the address it loaded from.
# ---------------------------------------------------------------------------

def rev(label, parts):
    """Five-instruction rounds of the mask-and-shift bit reversal GCC emits."""
    return [(op, "reverse", f"{label}: {what}") for op, what in parts]

GCC_REVERSE_IN = (
    rev("Reverse · bytes", [("andi", "keep the low byte"), ("slli", "park the value in the top half"),
                            ("slli", "low byte moves up"), ("srli", "high byte moves down"),
                            ("or", "combine → {v}")]) +
    rev("Reverse · nibbles", [("and", "keep the low nibbles (mask 0x0F0F, in t6)"),
                              ("and", "keep the high nibbles (mask 0xF0F0, in t1)"),
                              ("srli", "high nibbles move down 4"), ("slli", "low nibbles move up 4"),
                              ("or", "combine → {v}")]) +
    rev("Reverse · bit pairs", [("and", "mask 0x3333 (a7)"), ("and", "mask 0xCCCC (a6)"),
                                ("srli", "move down 2"), ("slli", "move up 2"), ("or", "combine → {v}")]) +
    rev("Reverse · bits", [("and", "mask 0x5555 (a0)"), ("and", "mask 0xAAAA (a1)"),
                           ("srli", "move down 1"), ("slli", "move up 1"),
                           ("or", "combine → {v}, the 16 bits in reverse order")])
)
GCC_REVERSE_OUT = (
    rev("Reverse back · bytes", [("slli", "park the value in the top half"),
                                 ("andi", "the new CRC's low byte is the entry's low byte"),
                                 ("srli", "high byte moves down"), ("slli", "low byte moves up"),
                                 ("or", "combine → {v}")]) +
    rev("Reverse back · nibbles", [("and", "mask 0x0F0F"), ("and", "mask 0xF0F0"),
                                   ("slli", "move up 4"), ("srli", "move down 4"), ("or", "combine → {v}")]) +
    rev("Reverse back · bit pairs", [("and", "mask 0x3333"), ("and", "mask 0xCCCC"),
                                     ("srli", "move down 2"), ("slli", "move up 2"), ("or", "combine → {v}")]) +
    rev("Reverse back · bits", [("and", "mask 0x5555"), ("and", "mask 0xAAAA"), ("slli", "move up 1"),
                                ("srli", "move down 1"),
                                ("or", "combine → {v}, the CRC in the order the protocol uses")])
)
GCC_SEQ = (
    [("lbu", "loop", "Load the next frame byte: {b}"), ("addi", "loop", "Advance the frame pointer"),
     ("xor", "lookup", "Fold the byte into the CRC → {v}")] +
    GCC_REVERSE_IN +
    [("srli", "lookup", "Lookup: the high byte, {b}, is the table index"),
     ("slli", "lookup", "×2: each entry is 2 bytes"),
     ("add", "lookup", "Add the base of GCC's table (t4)"),
     ("lhu", "lookup", "Load the entry: {v}, from a table in forward bit order"),
     ("or", "lookup", "Rebuild the reversed value, which the index step overwrote"),
     ("slli", "lookup", "Shift it up 8: the forward-order CRC update"),
     ("xor", "lookup", "Combine → the new CRC in forward bit order (low 16 bits: {v})")] +
    GCC_REVERSE_OUT +
    [("bne", "loop", "Next byte")]
)
TABLE_SEQ = [
    ("lbu", "loop", "Load the next frame byte: {b}"),
    ("srli", "lookup", "CRC >> 8: the high byte moves down ({v})"),
    ("addi", "loop", "Advance the frame pointer"),
    ("xor", "lookup", "Byte ^ CRC = {v}"),
    ("andi", "lookup", "Keep the low 8 bits: the table index, {b}"),
    ("slli", "lookup", "×2: each entry is 2 bytes"),
    ("add", "lookup", "Add the table base (a0) → {mem8}"),
    ("lhu", "lookup", "Load the entry: crc_itu_table[index] = {v}"),
    ("xor", "lookup", "Combine: (CRC >> 8) ^ entry = {v}, the new CRC"),
    ("bne", "loop", "Next byte"),
]
def bitwise_seq():
    seq = [("lbu", "loop", "Load the next frame byte: {b}"), ("li", "loop", "Bit counter = 8"),
           ("xor", "bits", "Fold the byte into the CRC → {v}")]
    for k in range(1, 9):
        seq += [("slli", "bits", f"Bit {k} of 8: copy bit 0 to the top of a register"),
                ("srai", "bits", "Spread it into a mask: {spread}"),
                ("srli", "bits", "Shift the CRC right one bit"),
                ("and", "bits", "Mask & polynomial (a3 holds 0x8408) → {poly}"),
                ("xor", "bits", "Apply: shifted CRC ^ {prevpoly} → {v}"),
                ("slli", "bits", "Keep 16 bits (the uint16_t cast), 1 of 2"),
                ("addi", "loop", "Count down the bits"),
                ("srli", "bits", "Keep 16 bits, 2 of 2"),
                ("bnez", "loop", "Next bit" if k < 8 else "All 8 bits done")]
    return seq + [("addi", "loop", "Advance the frame pointer"), ("bne", "loop", "Next byte")]

VARIANTS = [
    dict(id="bitwise", make=["CRC_IMPL=bitwise"], seq=bitwise_seq(),
         name="The bitwise definition", config="CRC_IMPL=bitwise · CRC pass pinned off",
         story="The loop as written in the source: eight shift-and-XOR steps per byte, made branchless by GCC.",
         crc="a4", show=["a4", "a5", "a2", "s0", "a1"], consts={"a3": "polynomial 0x8408, sign-extended"}),
    dict(id="gcc", make=["CRC_IMPL=bitwise", "ALGOFLAGS="], seq=GCC_SEQ,
         name="GCC's substituted table", config="CRC_IMPL=bitwise · CRC pass allowed",
         story="What 0001's -O2 build ran: GCC swapped the loop for a lookup table in forward bit order, "
               "so every byte is reversed on the way in and again on the way out.",
         crc="a5", show=["a5", "a4", "a3", "a2"],
         consts={"t6": "mask 0x0F0F", "t1": "mask 0xF0F0", "a7": "mask 0x3333", "a6": "mask 0xCCCC",
                 "a0": "mask 0x5555", "a1": "mask 0xAAAA", "t4": "GCC's table base"}),
    dict(id="table", make=[], seq=TABLE_SEQ,
         name="The stated table", config="CRC_IMPL=table · the 0008 reference",
         story="The textbook reflected table, written in the source. One lookup per byte and no reversal, "
               "because the table is built for the reflected polynomial.",
         crc="a4", show=["a4", "a5", "a2", "a3"], consts={"a0": "crc_itu_table base", "a1": "end of frame"}),
]


def die(msg):
    sys.exit(f"crc_anatomy: {msg}")


def clean_env():
    # Called from make, the environment carries the caller's MAKEFLAGS, including any
    # command-line variables (`make anatomy OPT=-O3`). The page describes fixed builds.
    return {k: v for k, v in os.environ.items() if not k.startswith(("MAKE", "MFLAGS"))}


def build(variant):
    args = ["make", "-s", "-C", HERE, "run", "OPT=-O2", "ARCH=rv32im"] + variant["make"]
    out = subprocess.run(args, capture_output=True, text=True, env=clean_env())
    if out.returncode:
        die(f"build failed for {variant['id']}:\n{out.stderr}")
    head = re.search(r"^--- (\S+)", out.stdout, re.M)
    get = lambda k: re.search(rf"^{k}\s*=\s*(\S+)", out.stdout, re.M)[1]
    return dict(elf=os.path.join(HERE, head[1]), image=get("image").split(":")[1],
                instret=int(get("instret"), 16), cc=re.search(r"^cc\s*=\s*(.*)$", out.stdout, re.M)[1])


def frame_address(elf):
    nm = subprocess.run(["riscv64-elf-nm", elf], capture_output=True, text=True, check=True).stdout
    m = re.search(r"^([0-9a-f]+) \w frame$", nm, re.M)
    return int(m[1], 16) if m else die(f"no `frame` symbol in {elf}")


def window(elf):
    """The first byte of the reference CRC, from Spike's commit log."""
    with tempfile.NamedTemporaryFile(suffix=".log") as log:
        subprocess.run(["spike", "-l", "--log-commits", f"--log={log.name}", "--isa=rv32im", elf],
                       capture_output=True, check=True)
        lines = open(log.name).read().splitlines()
    dis = re.compile(r"core\s+0: (0x[0-9a-f]+) \((0x[0-9a-f]+)\) (.*)$")
    com = re.compile(r"core\s+0: \d (0x[0-9a-f]+) \((0x[0-9a-f]+)\)(.*)$")
    regs, steps, init, asm, seen_commit = {}, [], None, None, False
    for line in lines:
        m = com.match(line)
        if m:
            seen_commit = True
            pc, _, rest = m.groups()
            writes = [(ABI[int(r)], v) for r, v in re.findall(r"(?:^|\s)x\s*(\d+) (0x[0-9a-f]+)", rest)]
            mem = re.findall(r"mem (0x[0-9a-f]+)", rest)
            if asm and asm.split()[0] == "lbu":
                if init is not None:
                    return steps, init
                init = dict(regs)
            if init is not None:
                steps.append(dict(pc=pc, asm=re.sub(r"\s+", " ", asm), w=writes, mem=mem[0] if mem else None))
            for r, v in writes:
                regs[r] = v
            continue
        m = dis.match(line)
        if m:
            asm = m.group(3).strip()
    if not seen_commit:
        die("Spike wrote no commit lines. It needs to be built with --enable-commitlog (README.md).")
    die(f"no complete byte window found in the trace of {elf}")


def label(variant, steps):
    seq = variant["seq"]
    got = [s["asm"].split()[0] for s in steps]
    want = [op for op, _, _ in seq]
    if got != want:
        k = next((i for i, (g, w) in enumerate(zip(got, want)) if g != w), min(len(got), len(want)))
        die(f"{variant['id']}: the executed sequence no longer matches the notes written for it.\n"
            f"  first difference at instruction {k + 1}: executed {got[k] if k < len(got) else '(end)'!r}, "
            f"notes expect {want[k] if k < len(want) else '(end)'!r}\n"
            f"  ({len(got)} executed, {len(want)} described). Update the sequence in crc_anatomy.py.")
    out, prev = [], 0
    poly = lambda x: "0x8408" if (x & 0xFFFF) == 0x8408 else "0"
    for s, (_, cat, note) in zip(steps, seq):
        v = int(s["w"][0][1], 16) if s["w"] else 0
        fill = dict(v=f"0x{v & 0xFFFF:04X}", b=f"0x{v & 0xFF:02X}", mem8=f"0x{v:08X}",
                    spread="bit 0 was 1 → all ones" if v == 0xFFFFFFFF else "bit 0 was 0 → zero",
                    poly=poly(v), prevpoly=poly(prev))
        out.append(dict(pc=s["pc"], asm=s["asm"], cat=cat, note=note.format(**fill), w=s["w"], mem=s["mem"]))
        prev = v
    return out


def capture_for(image):
    """The most recent capture whose run printed this loaded-image hash."""
    hits = [p for p in glob.glob(os.path.join(ROOT, "docs/results/*/stdout.txt"))
            if f"sha256:{image}" in open(p).read()]
    return os.path.basename(os.path.dirname(max(hits))) if hits else None


def main():
    programs = []
    for v in VARIANTS:
        b = build(v)
        steps, init = window(b["elf"])
        if steps[0]["mem"] is None or int(steps[0]["mem"], 16) != frame_address(b["elf"]):
            die(f"{v['id']}: the window's first load is not the frame's first byte")
        steps = label(v, steps)
        n = len(steps)
        crc_final = [val for s in steps for r, val in s["w"] if r == v["crc"]][-1]
        programs.append(dict(
            id=v["id"], name=v["name"], config=v["config"], story=v["story"], crc=v["crc"],
            show=v["show"], consts=v["consts"], steps=steps,
            init={r: init.get(r) for r in v["show"] + list(v["consts"])},
            instret=b["instret"], image=b["image"][:12], capture=capture_for(b["image"]),
            perByte=n, outside=b["instret"] - n * BYTES,
            counts={c: sum(s["cat"] == c for s in steps) for c in ("lookup", "reverse", "bits", "loop")
                    if any(s["cat"] == c for s in steps)},
            crcBefore=init.get(v["crc"]), crcAfter=crc_final, byteIn=steps[0]["w"][0][1]))
        print(f"  {v['id']:<8} {n:>3} per byte   instret {b['instret']:>9,}   image {b['image'][:12]}   "
              f"capture {programs[-1]['capture'] or '(none)'}")
    ends = {int(p["crcAfter"], 16) & 0xFFFF for p in programs}
    if len(ends) != 1:
        die(f"the three programs disagree on the CRC after the byte: {sorted(map(hex, ends))}")

    git = lambda *a: subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True).stdout.strip()
    spike = subprocess.run(["spike", "--help"], capture_output=True, text=True)
    meta = dict(commit=git("rev-parse", "--short", "HEAD"),
                dirty=bool(git("status", "--porcelain", "--untracked-files=no")),
                cc=b["cc"],
                spike=(spike.stdout + spike.stderr).splitlines()[0])
    data = json.dumps(dict(programs=programs, meta=meta), separators=(",", ":"))
    if "</script" in data:
        die("data would close its own <script> tag")
    page = open(os.path.join(HERE, "crc_anatomy.html")).read().replace("__DATA__", data)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    out = os.path.join(HERE, "build", "crc-byte-anatomy.html")
    open(out, "w").write(page)
    open(out.replace(".html", ".standalone.html"), "w").write(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>\n'
        + page + "\n</body></html>\n")
    print(f"  wrote {os.path.relpath(out, ROOT)} (and .standalone.html)"
          + ("   NOTE: working tree has uncommitted changes" if meta["dirty"] else ""))


if __name__ == "__main__":
    main()
