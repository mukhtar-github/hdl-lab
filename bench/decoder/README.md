# bench/decoder — the reference decoder's harness

**Benchmark type: specification-derived reconstruction.** Recorded on the day it was written,
2026-10-02, per `bench/README.md` rule 3. The decoder that will run here is written from the GT06
vendor document and Traccar's decoders, both pinned in `reference/README.md`. Nothing here is
instrumented production code.

This directory holds the harness that `decisions/0014` specifies, and two test decoders. The
reference decoder itself is the next step (`docs/HANDOFF.md`).

```
protocol specification → stimulus generator → reference decoder → expected output → Spike reference
                                              ^^^^^^^^^^^^^^^^^
```

## Run it

```bash
make -C bench/stimulus                       # the coverage stimulus, if it is not there yet
make -C bench/decoder run                    # the stub decoder, on the coverage stimulus
make -C bench/decoder check                  # both test decoders, each held to expect.py,
                                             # and one decoder image for two stimuli
make -C bench/decoder mutate                 # break the harness 16 ways: each must be caught
make -C bench/decoder run STIM=<dir> DECODER=<stub|format_test>
```

`STIM` is a directory that `bench/stimulus` wrote. The run refuses a `stimulus.bin` whose hash is
not the one in that directory's `manifest.json`.

## What a run prints

Before Spike starts, the Makefile prints what is about to run:

```
--- build/<hash>/decoder.elf   (spike --isa=rv32im) ---
cc       = riscv64-elf-gcc (GCC) 16.2.0
cflags   = -march=rv32im -mabi=ilp32 -mtune=rocket -mcmodel=medany -O2 -fno-optimize-crc ...
source   = stub.c
image    = sha256:<every byte that Spike loads>
decoder  = sha256:<the same, without the stimulus>
stimulus = sha256:<the linked stimulus.bin>
manifest = matches ../stimulus/build/coverage-1/manifest.json
```

After the window, the program prints, in this order (`decisions/0014`, section 6):

```
format      = 2
chunks      = 484
connections = 12
payload     = 11566
detection   = none
instret     = <the window's count, 64 bits>
records     = 496
<one line per record, in canonical order>
end         = 496
```

The last line repeats the number of records, so a run whose output was cut short cannot pass.

## The files

| File | What it is |
|---|---|
| `harness.c` | Checks `stimulus.bin`, sets up each connection, counts the window, then sorts, formats and prints the records |
| `records.h` | The record buffer: how a decoder hands each record on, inside the window |
| `decoder.h` | The interface between the harness and a decoder |
| `output.c`, `output.h` | Text output through Spike's syscall proxy, `SYS_write`, 4,096 bytes at a time |
| `stimulus.S` | Links `stimulus.bin` into the image, as data the compiler cannot see |
| `link.ld` | The image's layout. The stimulus comes last, so no address in the decoder depends on its size |
| `stub.c` | A test decoder that decodes nothing. It records every chunk, then each connection's length |
| `format_test.c`, `format_test.expected` | A test decoder for the formatter, and the text it must print, written out by hand |
| `expect.py` | Holds a run's output to what its test decoder must print |
| `mutate.py` | Breaks the harness on purpose, and checks that something catches each fault |
| `Makefile` | `make`, `make run`, `make check`, `make mutate`, `make clean` |

`crt0.S` and `htif.c` are `bench/rv32`'s, unchanged, so the CRC reference image cannot move.

## What the window counts

As `decisions/0014`, section 3, fixes it:

- **Inside:** the walk over the chunks, one load for each chunk header; `decoder_chunk` for each
  chunk, which dispatches to the connection's protocol and decodes; and `decoder_end`, because the
  end of the input ends every connection's stream.
- **Before:** the check of `stimulus.bin`, the trap handler, and `decoder_init`, which sets up each
  connection from the protocol table.
- **After:** the sort into canonical order, the formatter and the output.

The count reads `instret` and `instreth`, so it does not wrap after 4,294,967,296 instructions.

## The record buffer

A decoder appends each record as 32-bit words: a header, then its fields in any order, each an id
and a value (`records.h`). The id says the field's kind, and the ids follow the names' alphabetical
order. After the window, the formatter sorts each record's fields by id, and writes numbers in
decimal and `device`, `bytes` and `text` in hex. It reads the record buffer and nothing else.

This choice sets part of the count. A 32-bit field costs two stores, and a record's header two
more. That is per-record work, neither Prediction A's term nor B's (`decisions/0014`).

The connections' state and the records sit in the memory after the stimulus, up to `MEM_TOP`. Its
default is `0x90000000`, 256 MiB from Spike's DRAM base.

## What the harness refuses

| Exit code | When |
|---|---|
| 2 | `stimulus.bin` is refused: anything that `bench/stimulus/container.py` refuses, or no connections, or more than 65,536 |
| 3 | Memory runs out below `MEM_TOP` |
| 4 | A record in the buffer is malformed |
| 5 | Spike's host refuses a write |
| 6 | A trap. The harness prints `mcause` and `mepc`, and stops |

The harness cannot check the file's length, because no code may depend on the stimulus's size
(`decisions/0014`, section 1). The Makefile's hash check against `manifest.json` covers a file that
was cut short.

## Checking

- **`stub`:** `expect.py` predicts every line the stub prints from `stimulus.bin` alone. It reads
  the file through `bench/stimulus/container.py`, not through the harness's reader.
- **`format_test`:** ten records that use every field name, every kind of value at its extremes,
  every status and every form of type. The expected text was written by hand from SPEC §3.
- **One decoder image:** two stimuli give two images, but one image without the stimulus.
- **`make mutate`:** ten faults in the source and six corrupted stimuli. Each must end in a
  non-zero exit.

**The limit:** one person wrote the harness and its checks. When they agree, they are consistent
with each other, not necessarily right. The test decoders' instruction counts measure nothing, and
must never be quoted.

**Found while writing it:** without a trap handler, a fault in the chunk walk made a misaligned
load. The trap jumped to address 0, and Spike ran for more than 10 minutes until it was stopped by
hand. Now any trap ends the run with exit code 6.

## What it does not do yet

- **Decode.** The reference decoder is the next step.
- **The `0010` check** of the decoder's records against `intent.jsonl`. It comes after the decoder.
- **Run on the core.** The core's testbench must serve `SYS_write`, and the core must have
  `instreth`, by Phase 3 (`decisions/0014`).
