# ============================================================
# bench/rv32 — bare-metal RV32 targets for the Spike reference
#
#   make            build every reference program
#   make run        build and run each one under Spike
#   make check      run, then hold the reference lines to crc_oracle.py
#   make dump       disassemble
#   make anatomy    the CRC Byte Anatomy page, from Spike's commit log
#   make htif-cost  what each way of printing costs under Spike
#   make clean
#
# Homebrew's riscv64-elf-gcc is a FREESTANDING compiler: there is no
# newlib, no crt0.o, no libc. That is fine and in fact preferable —
# the benchmark will run on our core with no libc either, so a reference
# measured through newlib's printf would partly be measuring newlib.
# Output goes through Spike's HTIF instead (htif.c).
# ============================================================

CC      := riscv64-elf-gcc
OBJCOPY := riscv64-elf-objcopy
OBJDUMP := riscv64-elf-objdump
SPIKE   := spike
PYTHON  := python3
SHA256  := shasum -a 256

# ISA, ABI and tuning are configuration, and every result must declare them.
# Not because changing them always moves the instruction count — for
# crc_itu_ref.c, rv32i and rv32im produce the identical image
# (docs/experiments/0001) — but because they bound what the compiler may
# emit, and ARCH also bounds what Spike will execute.
#
# TUNE is pinned because GCC's default is otherwise invisible: it appears in
# neither this file nor the compiler's version line, and it moves the count
# (-mtune=sifive-7-series retires 618,641 where rocket retires 630,653).
ARCH    := rv32im
ABI     := ilp32
TUNE    := rocket
OPT     := -O2

# decisions/0008: the source states the algorithm, and the compiler may not
# substitute one. GCC 15+ recognises a bitwise CRC loop and swaps in an
# algorithm of its own choosing: at -O2 it replaced the source's loop with a
# 512-byte table (experiments/0001). Clear ALGOFLAGS only in an experiment
# that is about that pass, and say so. Never for a reference result.
ALGOFLAGS := -fno-optimize-crc

# Which form of CRC-ITU crc_itu_ref.c runs. `table` is the reference.
# `bitwise` is the definition, kept for experiments — never the reference.
CRC_IMPL  := table

ARCHFLAGS := -march=$(ARCH) -mabi=$(ABI) -mtune=$(TUNE) -mcmodel=medany
CFLAGS    := $(ARCHFLAGS) $(OPT) $(ALGOFLAGS) -DCRC_IMPL_$(CRC_IMPL) \
             -ffreestanding -fno-builtin -Wall -Wextra -Werror
LDFLAGS   := $(ARCHFLAGS) -nostdlib -nostartfiles -T link.ld \
             -Wl,--no-warn-rwx-segments   # no MMU here; one RWX LOAD segment is correct

COMMON  := crt0.S htif.c
PROGS   := crc_itu_ref
INPUTS  := $(addsuffix .c,$(PROGS)) $(COMMON) link.ld htif.h

# Each build lives in a directory named by a hash of everything that goes into
# it: the compiler's identity, every flag, and the bytes of every input. One
# configuration cannot run another's binary, because it builds somewhere else.
# Without this, `make run OPT=-O3` over an -O2 build re-ran the -O2 binary and
# reported it under -O3 (docs/bugs/0004).
#
# No timestamp is involved, deliberately. The first fix was a flags stamp that
# the ELF depended on, and it failed the same way whenever two configurations
# were built within one second: this host's GNU make 3.81 compares mtimes to
# the second, so a stamp rewritten in the same second as the last build does
# not count as newer. Do not override BUILD — that bypasses all of this.
CC_ID     := $(shell $(CC) --version 2>/dev/null | head -n 1)
CONFIG    := $(strip $(CC_ID) | $(CFLAGS) | $(LDFLAGS))
CONFIG_ID := $(shell { printf '%s\n' '$(CONFIG)'; cat $(INPUTS); } | $(SHA256) | cut -c1-12)
BUILD     := build/$(CONFIG_ID)

ELFS    := $(addprefix $(BUILD)/,$(addsuffix .elf,$(PROGS)))
IMAGES  := $(ELFS:.elf=.bin)

.PHONY: all run check clean dump anatomy htif-cost

all: $(ELFS)

$(BUILD):
	@mkdir -p $@ && printf '%s\n' '$(CONFIG)' > $@/config.txt

$(BUILD)/%.elf: %.c $(COMMON) link.ld htif.h | $(BUILD)
	@$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(COMMON) $<

# The loaded image: every byte Spike loads, none of the ELF's metadata. Its hash
# is what identifies the program that ran. rv32i and rv32im builds of
# crc_itu_ref.c differ as ELFs (the ISA attribute string) but not as images.
$(BUILD)/%.bin: $(BUILD)/%.elf
	@$(OBJCOPY) -O binary $< $@

# Everything a result needs to say what ran is printed before it runs, so
# scripts/capture.sh records it without being told.
# --isa must match what the ELF was built for, or Spike will trap on the
# first instruction the ISA string does not permit.
run: $(ELFS) $(IMAGES)
	@for e in $(ELFS); do \
		echo "--- $$e   (spike --isa=$(ARCH)) ---"; \
		echo "cc       = $(CC_ID)"; \
		echo "cflags   = $(strip $(CFLAGS))"; \
		echo "image    = sha256:$$($(SHA256) $${e%.elf}.bin | cut -d' ' -f1)"; \
		$(SPIKE) --isa=$(ARCH) $$e; \
	done

# Agreement between builds is consistency, not correctness. crc_oracle.py is an
# independent CRC-16/X-25, anchored to published values before it is trusted.
check: $(ELFS) $(IMAGES)
	@$(MAKE) --no-print-directory run > $(BUILD)/run.out || { cat $(BUILD)/run.out; exit 1; }
	@cat $(BUILD)/run.out
	@$(PYTHON) crc_oracle.py $(BUILD)/run.out

# One byte of each CRC form, instruction by instruction, from Spike's commit log.
# Builds its own three configurations whatever variables this make was given;
# stops if the code GCC emits no longer matches the notes written for it.
anatomy:
	@$(PYTHON) crc_anatomy.py

# What each way of printing costs under Spike, measured for decisions/0014. Not a
# reference program. Its ELFs are rebuilt on every run, so no stale binary can
# answer for a changed source (docs/bugs/0004). The three printing modes must
# print the same text, or this fails.
HTIF_COST  := build/htif-cost
HTIF_FLAGS := $(ARCHFLAGS) $(OPT) -ffreestanding -fno-builtin -Wall -Wextra -Werror

htif-cost:
	@rm -rf $(HTIF_COST) && mkdir -p $(HTIF_COST)
	@$(CC) $(HTIF_FLAGS) -DMODE_PUTCHAR -DN=102400u $(LDFLAGS) \
		-o $(HTIF_COST)/putchar.elf $(COMMON) htif_cost.c
	@$(CC) $(HTIF_FLAGS) -DMODE_WRITE -DN=102400u -DCHUNK=1u $(LDFLAGS) \
		-o $(HTIF_COST)/write-1.elf $(COMMON) htif_cost.c
	@$(CC) $(HTIF_FLAGS) -DMODE_WRITE -DN=102400u -DCHUNK=4096u $(LDFLAGS) \
		-o $(HTIF_COST)/write-4096.elf $(COMMON) htif_cost.c
	@$(CC) $(HTIF_FLAGS) -DMODE_COMPUTE -DN=100000000u $(LDFLAGS) \
		-o $(HTIF_COST)/compute.elf $(COMMON) htif_cost.c
	@echo "cc       = $(CC_ID)"
	@echo "cflags   = $(strip $(HTIF_FLAGS))"
	@for m in putchar write-1 write-4096 compute; do \
		/usr/bin/time -p $(SPIKE) --isa=$(ARCH) $(HTIF_COST)/$$m.elf \
			> $(HTIF_COST)/$$m.out 2> $(HTIF_COST)/$$m.time \
			|| { cat $(HTIF_COST)/$$m.out $(HTIF_COST)/$$m.time; exit 1; }; \
		sed '$$d' $(HTIF_COST)/$$m.out > $(HTIF_COST)/$$m.text; \
		$(OBJCOPY) -O binary $(HTIF_COST)/$$m.elf $(HTIF_COST)/$$m.bin; \
		echo "--- $$m   (spike --isa=$(ARCH)) ---"; \
		echo "image    = sha256:$$($(SHA256) $(HTIF_COST)/$$m.bin | cut -d' ' -f1)"; \
		echo "printed  = $$(wc -c < $(HTIF_COST)/$$m.text | tr -d ' ') bytes before the last line"; \
		tail -n 1 $(HTIF_COST)/$$m.out; \
		echo "wall     = $$(awk '/^real/ { print $$2 }' $(HTIF_COST)/$$m.time) s"; \
	done
	@cmp $(HTIF_COST)/putchar.text $(HTIF_COST)/write-1.text \
		&& cmp $(HTIF_COST)/putchar.text $(HTIF_COST)/write-4096.text \
		&& echo "text     = the three printing modes printed the same bytes"

dump: $(ELFS)
	@for e in $(ELFS); do $(OBJDUMP) -d $$e | head -40; done

clean:
	rm -rf build
