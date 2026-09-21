/* Spike's default DRAM base is 0x80000000. */
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
  . += 0x2000;          /* 8 KiB stack */
  _stack_top = .;
}
