# ============================================================
# bench/rv32 — bare-metal RV32 targets for the Spike reference
#
#   make            build every reference program
#   make run        build and run each one under Spike
#   make clean
#
# Homebrew's riscv64-elf-gcc is a FREESTANDING compiler: there is no
# newlib, no crt0.o, no libc. That is fine and in fact preferable —
# the core we are building will have no libc either, so a reference
# measured through newlib's printf would partly be measuring newlib.
# Output goes through Spike's HTIF instead (htif.c).
# ============================================================

CC      := riscv64-elf-gcc
OBJDUMP := riscv64-elf-objdump
SPIKE   := spike

# ISA and ABI are part of the reference, not a convenience. Changing either
# changes the instruction count, so both belong in every result manifest.
ARCH    := rv32im
ABI     := ilp32
OPT     := -O2

ARCHFLAGS := -march=$(ARCH) -mabi=$(ABI) -mcmodel=medany
CFLAGS    := $(ARCHFLAGS) $(OPT) -ffreestanding -fno-builtin -Wall -Wextra -Werror
LDFLAGS   := $(ARCHFLAGS) -nostdlib -nostartfiles -T link.ld \
             -Wl,--no-warn-rwx-segments   # no MMU here; one RWX LOAD segment is correct

BUILD   := build
COMMON  := crt0.S htif.c
PROGS   := crc_itu_ref

ELFS    := $(addprefix $(BUILD)/,$(addsuffix .elf,$(PROGS)))

.PHONY: all run clean dump

all: $(ELFS)

$(BUILD):
	@mkdir -p $(BUILD)

$(BUILD)/%.elf: %.c $(COMMON) link.ld htif.h | $(BUILD)
	@$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(COMMON) $<

# --isa must match what the ELF was built for, or Spike will trap on the
# first instruction the ISA string does not permit.
run: $(ELFS)
	@for e in $(ELFS); do \
		echo "--- $$e   (spike --isa=$(ARCH)) ---"; \
		$(SPIKE) --isa=$(ARCH) $$e; \
	done

dump: $(ELFS)
	@for e in $(ELFS); do $(OBJDUMP) -d $$e | head -40; done

clean:
	rm -rf $(BUILD)
