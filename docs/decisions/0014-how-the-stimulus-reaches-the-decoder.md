# 0014 — How the stimulus reaches the reference decoder, and how its records leave

- **Date:** 2026-09-30
- **Status:** Accepted
- **Phase:** 0, binding on the reference decoder's harness, on `stimulus.bin`, and on the `0010`
  check

## Context

`0011` and `0012` fixed what the reference decoder does and what it reports. Its harness is still
open. The harness is the code around the decoder. It puts the stimulus in memory, gives it to the
decoder, counts the decoder's work, and prints the records. The journal named three questions on
2026-09-29:

- **How the decoder learns each connection's protocol.** `0011` assumes that the decoder knows it
  before the connection's first byte, as Traccar does. Traccar runs one server per protocol
  (`Gt06Protocol.java:34-37`, `Jt808Protocol.java:52-56`). `stimulus.bin` does not carry the
  protocol (`bench/stimulus/README.md`).
- **Where records are serialised, relative to the measured window.** `0012` says that a record is a
  value, that its text is how the value is serialised, and that serialising is not decoding.
- **How the records leave Spike.**

A fourth question comes before all three: how `stimulus.bin` gets into Spike's memory. The stimulus
README says only "loaded or linked as a binary object, never compiled in as a C array".

**What Spike does, read from its source at the pinned commit** (`reference/README.md`):

- Its host side reads `tohost` once every `INTERLEAVE` = 5,000 instructions (`sim.h:104`,
  `sim.cc:202-219`). A program that waits for the host spins until then.
- It has two devices that print:
  - the console device writes one character per command (`device.cc:70-73`);
  - the syscall proxy reads eight 64-bit words at the address in `tohost` (`syscall.cc:448-460`).
    For `SYS_write`, it then writes a whole buffer to the host's standard output (`:240-246`).
- It can put a file in memory in three ways. With the default memory, `--kernel` loads a flat file at
  `0x80400000` on RV32, and `--initrd` loads one at the top of memory (`spike.cc:388-412`).
  `+payload=` loads a second ELF (`htif.cc:143-147`).

**What printing costs, measured** in
[`20260930T052623Z-spike-htif-cost`](../results/20260930T052623Z-spike-htif-cost/):

| Path | Instructions per command | Instructions per character | 102,400 characters took |
|---|---|---|---|
| console device, 1 character a command | 4,999.92 | 4,999.92 | 19.15 s |
| `SYS_write`, 1 character a command | 4,999.97 | 4,999.97 | 23.32 s |
| `SYS_write`, 4,096 characters a command | 4,866.96 | 1.19 | 0.08 s |

The cost belongs to the command, not to the byte. Spike ran 23.5 million instructions a second on
this Apple M2.

**How much a run prints is not measured,** because the decoder does not exist yet. An estimate from
`intent.jsonl`'s frame counts and SPEC §3's fields gives the coverage stimulus about 400 records and
60 KB of text. That is about 250 bytes a frame.

**Where the count is read today.** `crc_itu_ref.c` reads `instret` before and after its loop, and
prints after. riscv-tests' benchmarks do the same. They count between `setStats(1)` and
`setStats(0)`, then check and print (`median_main.c:34-39`, `syscalls.c:116-124`). The benchmark
reads only the low 32 bits of `instret` (`0009`, Decision 2). At 23.5 million a second, that half
wraps after 183 s of Spike.

**Where the stimulus must also run.** In Phase 3 the decoder runs on the core in RTL simulation, and
lockstep compares every retired instruction with Spike's (roadmap, rung 4). In Phase 4 the frozen
configurations run on the core. The core's testbench will load ELF files and watch `tohost` in any
case, because riscv-tests needs both (roadmap, rung 2).

**The same constraint as `0007`, `0009`, `0011` and `0012`.** These choices decide what the window
contains, so they decide how the count divides between Predictions A and B. They may not be chosen
for that effect. The effect is stated under *Consequences*.

## Options considered

### How `stimulus.bin` gets into memory

1. **Link it into the decoder's ELF, in a section of its own.** An assembly file includes the file's
   bytes with `.incbin`.
   - *For:* the ELF holds the whole run. Spike, the core's testbench and lockstep load it the same
     way, and no Spike option is involved. The compiler sees a symbol, never the bytes.
   - *Against:* each stimulus needs its own link. The image hash then covers the stimulus too, so a
     run must also identify the decoder alone.
2. **Spike's `--kernel` option.**
   - *For:* one ELF serves every stimulus.
   - *Against:* it uses an option for Linux kernels to carry data. Its address, `0x80400000`, must
     agree in the linker script, the Spike command and every testbench. The decoder's image must end
     below it.
3. **A second ELF, with `+payload=`.** The same as option 2, with a conversion step, and only
   through Spike's host side.
4. **Read the file at run time through the syscall proxy:** `getmainvars` for its path, then
   `openat` and `read`.
   - *For:* one ELF, at any address.
   - *Against:* the core's testbench would have to serve three more calls. Lockstep and Phase 4 would
     need a second route for the input. It also adds target code to a harness, and this project's
     harnesses have lied before (`bench/rv32/README.md`).
5. **A C array, compiled in.** Forbidden. In `experiments/0001`, a build that could see its input
   did a sixth of its work and still printed the right answers (`bench/README.md`).

### How the decoder learns each connection's protocol

1. **A table in `stimulus.bin`, with one protocol for each connection.** It stands in for the port
   that a connection arrived on, as the connection id stands in for the connection.
   - *For:* it is what `0011` assumes and what Traccar does. The generator already knows each
     connection's protocol, and writes it to `intent.jsonl`.
   - *Against:* the format changes. The generator, `check.py` and their tests change, and every
     stimulus is made again. None is committed (SPEC §8), so nothing stored goes stale.
2. **Detect it from each connection's first bytes.**
   - *For:* the file does not change.
   - *Against:* Traccar does not do this, so no pinned source says how. `0011`'s search would gain
     the other protocol's start bytes, and `0011` says that it must then be revisited. Detection
     would also work only because rule R2 puts a clean session frame first, and R2 is an
     assumption.
3. **A rule on connection ids,** for example that GT06 connections come first.
   - *Against:* no file states the rule. If the generator dealt connections another way, the decoder
     would misread them and report no error.
4. **A protocol field in every chunk header.**
   - *Against:* it repeats a fact about the connection in every chunk, so the file could contradict
     itself. The chunk header would also grow past one word, which the harness reads with one load.
5. **One file for each protocol.**
   - *Against:* the decoder would take all of one protocol's chunks before any of the other's. SPEC
     §7 says that connections interleave at line rate, and that a stimulus without interleaving
     measures a locality that does not exist.

### Where records are serialised

1. **Inside the window, printed as the decoder makes them.**
   - *Against:* at 4,999.92 instructions a character, one 250-byte record adds about 1.25 million
     instructions of spinning to the count. That count measures Spike's polling interval, not
     decoding.
2. **As text inside the window, printed after it.**
   - *Against:* writing digits and field names is not decoding (`0012`). Traccar decodes every
     location into a `Position` object, not text (`PROTOCOL-EVIDENCE` Finding 9). The window would
     count work that Traccar's decoders do not do.
3. **As values inside the window, and as text after it.** The decoder appends each record's value to
   a buffer. After the window, the harness sorts the records into canonical order, formats them and
   prints them.
   - *For:* the window holds the decoding and the stores that hand each record on. A deployed
     decoder also hands each record on.
   - *Against:* every record of a run stays in memory until the window ends.
4. **Pause the count while each chunk's records print.**
   - *For:* it seems to need memory for one chunk's records, not for a run's.
   - *Against:* it does not save that memory. Canonical order is by connection, and a connection's
     records can arrive until its last chunk. So no record can print in canonical order before the
     input ends. Each pause also adds counter reads to the count. On the core, the printing code
     would run between the counted intervals and change the state that each interval starts from,
     such as a cache's.
5. **Run the decoder twice, count one run, and print the other.**
   - *Against:* the check would then judge a run that was not counted.

### How records leave Spike

1. **The console device, one character per command,** as `crc_itu_ref.c` prints today.
   - *Against:* it costs 4,999.92 instructions and 187 µs a character. The coverage run's estimated
     60 KB would take about 11 s. A benchmark run would take about 47 s for every 1,000 frames, at
     the estimated 250 bytes a frame.
   - *Also against, read from code and not observed:* `htif_putchar` stores the character's word of
     `tohost` before the command's word (`0x8000006c`, then `0x80000070`, in the reference image
     `1baf3e07…`). Spike's host can run between any two instructions (`sim.cc:202-219`). If it runs
     between those two stores, it reads a command for the syscall proxy instead. An odd character
     then ends the run as a failure (`syscall.cc:196-201`). The proxy reads an even one as the
     address of a parameter block (`:448-451`).
2. **The syscall proxy's `SYS_write`, one buffer per command.**
   - *For:* 1.19 instructions a character, in buffers of 4,096 bytes. riscv-tests' own benchmarks
     print through the same call (`syscalls.c:20-36`). Its command's upper word is zero, so a
     half-written command is never a different command.
   - *Against:* to run the same ELF, the core's testbench must serve it. The testbench must read
     eight words at an address, then write the bytes they point to. riscv-tests needs only the exit
     command.
3. **Spike's signature dump.** The records go to a memory region, and Spike writes the region to a
   file at exit (`+signature=`, `htif.cc:171-191`).
   - *For:* the program sends no command while it runs.
   - *Against:* the region's size is fixed when the program is linked. Spike writes all of it in hex,
     16 bytes a line, each line's bytes in reverse order, so the text needs a converter. Nothing marks
     where the records end.
4. **Read memory through Spike's debug interface.**
   - *Against:* it is interactive, and no tool in this project uses it.

## Decision

**The input: option 1. The protocol: option 1. Serialising: option 3. The output: option 2.**

### 1. The stimulus is linked into the decoder's image

- An assembly file includes `stimulus.bin`'s bytes in a section of their own, on a 4-byte boundary,
  after every section of the decoder. The compiler sees only a symbol.
- The decoder reads sizes from the stimulus's header, never from a symbol that depends on the
  stimulus. So a decoder has one image without its stimulus, whatever stimulus it runs.
- The build directory is named by a hash of the stimulus's bytes too, as it is by every other input
  (`docs/bugs/0004`).
- Before each run, the Makefile prints three hashes:
  - `image`: every byte that Spike loads;
  - `decoder`: the image without the stimulus's section;
  - `stimulus`: the linked file. It must equal the hash in that stimulus's `manifest.json`.

### 2. `stimulus.bin` version 2 carries each connection's protocol

```
header   "TFDS" | u16 format version (2) | u16 header bytes (20)
         | u32 chunks | u32 connections | u32 payload bytes (chunk data, no padding)
table    u8 protocol per connection: 1 GT06, 2 JT808 | zeros to a multiple of 4
chunk    u16 length | u16 connection | length bytes | zeros to a multiple of 4
```

- The table stands in for the port that each connection arrived on. It is transport metadata, like
  the connection id. The decoder chooses each connection's framing from it, and may not parse a
  protocol out of the payload (SPEC §3).
- 0 is not a protocol, so a table of zeros fails.
- Before the window, the harness reads the whole file once. It refuses anything that
  `container.unpack` refuses, and any other version or protocol code. A refused file ends the run
  with a non-zero exit code.

### 3. The window

The window is the interval over which the harness counts retired instructions.

**Inside it:**
- the harness's walk over the chunks: one load for each chunk header, and the loop;
- for each chunk, the dispatch to its connection's protocol;
- everything that `0011` and `0012` require of the decoder: the search, framing, the check, fields,
  units, the device binding and the bytes of each response;
- the stores that append each record's value to the record buffer;
- the end of the input. It ends every connection's stream, so `0011` rule 7 applies to each
  connection.

**Before it:** the check of the file, and the setup of each connection's state from the table. The
setup stands in for accepting a connection, before its first byte.

**After it:** everything else. The harness sorts the records into canonical order, formats them and
prints them.

**The count has 64 bits.** The harness reads `instret` and its upper half, `instreth`. The low half
alone wraps after 4,294,967,296 instructions, 183 s of Spike, and a wrapped count shows no sign that
it is wrong.

### 4. The record buffer, and the formatter

- **Every value is final before the window ends.** Each field is in the record buffer in the unit
  that its text shows. Each response's bytes are built.
- **The formatter only turns values into text.** It reads the record buffer and nothing else: no
  byte of the stimulus, and no state of the decoder. It writes numbers in decimal, and `device`,
  `bytes` and `text` in hex (`0012`, section 7). It converts no unit, checks nothing and chooses no
  field. So no decoding work can leave the window.
- **The decoder appends records in the order it makes them.** After the window, a stable sort by
  connection gives `0012`'s canonical order, because each connection's records are already in stream
  order.

### 5. The output

- **All output goes through the syscall proxy's `SYS_write`,** to the host's standard output, one
  text buffer at a time.
- **The last line repeats the number of records.** The `0010` check refuses output that has no such
  line, or whose number differs. `bench/rv32`'s harness once lost its last character and reported no
  error.

### 6. What each run prints

- **Before the run, from the Makefile:** the compiler, the flags and the three hashes.
- **After the window, from the program,** in this order:
  - the stimulus header's values: format version, chunks, connections and payload bytes;
  - the detection mode (`0007`). It is chosen when the image is built, so the image hash identifies
    it;
  - `instret`, the window's count;
  - the number of records;
  - the records, in canonical order;
  - the last line.

## Consequences

**Made easier.**
- **One ELF holds a run:** the decoder and its stimulus. Spike, the core's testbench and lockstep load
  the same bytes, so Phase 4 compares the core with Spike on one program.
- **The window holds decoding and the hand-off of each record.** Its count does not depend on the
  output path, the formatter or Spike's polling interval.
- **Printing no longer limits the size of a run.** At 1.19 instructions a character, 102,400
  characters took 0.08 s.
- **The `0010` check reads one form:** header lines, records in canonical order, and a last line to
  hold the count to.

**Made harder, or given up.**
- **Each stimulus needs its own link,** and each run prints three hashes.
- **`stimulus.bin` changes to version 2.** `container.py`, `check.py` and `test_stimulus.py` change.
  This record does not change them. That is the next step, before any decoder code.
- **Every record of a run stays in memory until the window ends.** Spike gives the program 2,048 MiB
  by default (`spike.cc:383`). A platform with less memory may need a smaller configuration, or the
  paused count rejected above.
- **The formatter is new code that nothing counts.** The `0010` check holds its output to the intent
  log, so a formatter fault shows as a mismatch there.
- **The core's testbench must serve `SYS_write`** before the core runs the decoder, in Phase 3.
- **The core needs `instreth` by Phase 3,** because the harness reads it. That settles part of an
  open item in `0009`, "Counters beyond the low half of `instret`".
- **A run prints about 250 bytes a frame** (estimated), so a run of 10,000 frames prints about
  2.5 MB. `0010` says that each capture records the decoder's output. The step that declares the
  configurations decides whether a capture keeps all of it, or its hash and the check's verdict.
- **`crc_itu_ref.c` keeps `htif_putchar`.** Its risk from the two stores is read from code, and not
  observed. Every capture of it passed the oracle, and the place where its first command falls is
  fixed for a given image. A sweep over that place would show the risk, or rule it out.

**Effect on the predictions.** The window counts one dispatch for each chunk. Chunk size is an
assumption with no source (SPEC, amendment of 2026-09-27). So it sets part of the count, as it
already did through one load for each chunk. The stores that hand on each record are per-record work.
That is neither A's term nor B's, so it dilutes the share of each. The formatter's work, which is
also neither, stays outside. None of this was a criterion. Each choice would have been the same if
either prediction were already known to be right.

**Revisit if:**
- a platform cannot hold a run's record buffer;
- Spike is upgraded. Run `make -C bench/rv32 htif-cost` again first;
- the core's testbench cannot serve `SYS_write`;
- a pinned source shows a server that learns a connection's protocol from its bytes.

## Predictions

None. This record fixes an interface. The one fact it rests on, what a command costs, is measured.
