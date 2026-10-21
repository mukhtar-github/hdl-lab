/* The reference decoder's image (decisions/0014). It loads at Spike's DRAM base, as
   bench/rv32/link.ld does. The stimulus comes last, so no address in the decoder depends on its
   size, and `objcopy -R .stimulus` gives one image for every stimulus. The memory after the
   stimulus, up to MEM_TOP, holds the connections' state and the records (harness.c). */
OUTPUT_ARCH( "riscv" )
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;

  .text.init : { *(.text.init) }
  .text      : { *(.text) *(.text.*) }
  .rodata    : { *(.rodata) *(.rodata.*) *(.srodata) *(.srodata.*) }
  .data      : { *(.data) *(.data.*) *(.sdata) *(.sdata.*) }

  /* tohost/fromhost live here, on their own page, so nothing else shares it. */
  .htif ALIGN(4096) : { KEEP(*(.htif)) }

  .bss ALIGN(16) :
  {
    _bss_start = .;
    *(.bss) *(.bss.*) *(.sbss) *(.sbss.*) *(COMMON)
    _bss_end = .;
  }

  . = ALIGN(16);
  . += 0x10000;         /* 64 KiB stack */
  _stack_top = .;

  .stimulus ALIGN(16) : { KEEP(*(.stimulus)) }
}
