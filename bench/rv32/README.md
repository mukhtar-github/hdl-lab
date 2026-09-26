# bench/rv32 — bare-metal RV32 targets and the Spike reference

**Benchmark type: specification-derived reconstruction.** Recorded here on the day it was
written, per `bench/README.md` rule 3 and `docs/decisions/0004`.

Stimulus is synthesised from the published GT06 layout. The terminal ID in `crc_itu_ref.c` is
the obviously-fake sequence `01 23 45 67 89 AB CD EF`. **No captured operational data, no real
IMEI, no forum hex.** Nothing here came from the FleetPoynt trace, and nothing here is
instrumented production software.

## Why bare metal, with no libc

Homebrew's `riscv64-elf-gcc` is a *freestanding* compiler — no newlib, no `crt0.o`, no `libc`.
Compiling works; linking against a C library does not, because there is no C library.

That constraint turned out to be the right target anyway:

```
the core we are building will have no OS and no libc
        ↓
a reference measured through newlib's printf
        ↓
would partly be measuring newlib
```

So output goes through Spike's HTIF directly (`htif.c`), and `crt0.S` is 12 instructions. The
reference program's instruction count is the decode work and nothing else.

## Layout

| File | What it is |
|---|---|
| `crt0.S` | Startup: set `sp`, zero `.bss`, call `main`, exit through HTIF |
| `htif.h` / `htif.c` | `putchar` / `puts` / hex / `exit` over Spike's host-target interface |
| `link.ld` | Loads at `0x80000000` (Spike's DRAM base); gives `tohost`/`fromhost` their own page |
| `crc_itu_ref.c` | CRC-ITU over a GT06-shaped frame — the smallest real piece of the decoder. Two forms, chosen with `CRC_IMPL`: `table` is the reference, `bitwise` is the definition (`decisions/0008`) |
| `crc_oracle.py` | An independent CRC-16/X-25, anchored to published values, that checks a run's reference lines |
| `crc_anatomy.py`, `crc_anatomy.html` | `make anatomy`: the CRC Byte Anatomy page. One byte of each CRC form, instruction by instruction, from Spike's commit log |
| `Makefile` | `make`, `make run`, `make check`, `make anatomy`, `make dump`, `make clean` |

## Toolchain, pinned

| Component | Version | How it was installed |
|---|---|---|
| Compiler | `riscv64-elf-gcc` 16.2.0 | `brew install riscv64-elf-gcc` (bottled) |
| Binutils | `riscv64-elf-ld` 2.47 | dependency of the above |
| Simulator | Spike **1.1.0**, tag `v1.1.0`, commit `530af85d83781a3dae31a4ace84a573ec255fefa`, configured `--enable-commitlog` | built from source, see below |

**Spike was not installed from the Homebrew tap, deliberately.** The tap's formula is
`url "https://github.com/riscv/riscv-isa-sim.git"` with `version "main"` — an *unpinned* git
branch with no source checksum, and its bottles are built for `sequoia` while this host is
`tahoe`, so it would have compiled whatever happened to be on `main` that day. Installing the
component that *defines the golden result* from a moving target defeats the purpose of having a
golden result. Installing it also requires `brew trust` on a third-party tap.

Built instead from the tagged release, with the commit verified against the tag listing:

```bash
git clone --depth 1 --branch v1.1.0 \
    https://github.com/riscv-software-src/riscv-isa-sim.git
cd riscv-isa-sim && git rev-parse HEAD   # must be 530af85d83781a3dae31a4ace84a573ec255fefa
mkdir build && cd build
../configure --prefix="$HOME/.local" --without-boost --without-boost-asio --without-boost-regex \
             --enable-commitlog
make -j"$(sysctl -n hw.ncpu)" && make install
```

**Rebuilt 2026-09-26 with `--enable-commitlog`**, same tag and commit. `spike --log-commits`
now prints every register and memory write, one line per retired instruction. That is what
checking the core against Spike instruction by instruction will need.

The rebuild was verified before it replaced anything. On six builds (the table form at -O0, -O2
and -O3; rv32i; the bitwise form with and without GCC's CRC pass), the program output and the
full `-l` execution trace, up to 1.3 million lines, were byte-identical to the previous
binary's. The version line reads `1.1.0` either way, so this paragraph is the only place the
difference is recorded.

## Run it

```bash
make -C bench/rv32 run      # build and run
make -C bench/rv32 check    # the same, then hold the reference lines to crc_oracle.py
```

Before it runs anything, `make run` prints what is about to run:

```
--- build/291a22f496ef/crc_itu_ref.elf   (spike --isa=rv32im) ---
cc       = riscv64-elf-gcc (GCC) 16.2.0
cflags   = -march=rv32im -mabi=ilp32 -mtune=rocket -mcmodel=medany -O2 ...
image    = sha256:69f46c09...
```

`image` hashes the **loaded image** (`objcopy -O binary`): every byte Spike loads and none of the
ELF's metadata. It is what identifies the program that ran. Two builds with different flags can
have the same image (rv32i and rv32im do, for this program), and one flag can change the image
without changing the instruction count (`-mtune=generic-ooo` does). `build/<hash>/` is named by
the compiler, the flags and the bytes of every input, so no configuration can run another's
binary.

`check` passing means the reference lines match a CRC computed by a different path from this
program's. Six builds agreeing with *each other* would not mean that: six compilations of a wrong
CRC agree perfectly.

**What the reference runs is stated, not chosen by the compiler** (`decisions/0008`). The
reference is `CRC_IMPL=table`, the byte-wise reflected table, built with `-fno-optimize-crc`, so
no compiler can swap in an algorithm of its own. At -O2 in `experiments/0001` it had done exactly
that. `CRC_IMPL=bitwise` is the definition, kept for experiments and never quoted as the reference.

Do not record a number from any of this by hand. Use `scripts/capture.sh`, which writes the
commit, the working-tree state and every tool version alongside the output.

## Two harness bugs found here, worth knowing about

`htif_exit` originally did not wait for Spike to consume the previous HTIF command before
writing the exit command. The result: **the last character of output was silently dropped** —
the trailing newline vanished, and nothing reported an error. A result whose final byte depends
on a race is not a result. `htif_exit` now drains `tohost` first.

The general shape of that is worth carrying: the harness is as capable of lying as the design
is, and it lies more quietly.

**The second one reported the wrong configuration.** The ELF rule depended on the sources but not
the flags. So `make run OPT=-O3` over an existing -O2 build re-ran the -O2 binary and printed its
instruction count under the -O3 command. Exit 0, clean tree, right commit. `capture.sh` recorded
every field correctly and the result was still wrong — preserved in `docs/bugs/0004`. The first
fix, a flags stamp, failed the same way whenever two builds landed within one second, because this
make compares timestamps to the second. Build directories are now named by a hash of their
inputs, so no timestamp is involved.
