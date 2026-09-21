#include "htif.h"

// Spike locates these two by symbol name, so they must keep these names and
// must be allocated (not .bss-eliminated). The linker script gives them a
// section of their own.
volatile uint64_t tohost   __attribute__((section(".htif"), aligned(8)));
volatile uint64_t fromhost __attribute__((section(".htif"), aligned(8)));

static void htif_send(uint64_t dev, uint64_t cmd, uint64_t payload)
{
    // Wait for the host to consume the previous command before issuing another.
    while (tohost != 0)
        fromhost = 0;
    tohost = (dev << 56) | (cmd << 48) | payload;
}

void htif_putchar(int c)          { htif_send(1, 1, (uint8_t)c); }
void htif_puts(const char *s)     { while (*s) htif_putchar(*s++); }

static void put_nib(unsigned n)   { htif_putchar("0123456789abcdef"[n & 0xF]); }

void htif_puthex16(uint16_t v)
{
    for (int i = 12; i >= 0; i -= 4) put_nib(v >> i);
}

void htif_puthex32(uint32_t v)
{
    for (int i = 28; i >= 0; i -= 4) put_nib(v >> i);
}

void htif_exit(int code)
{
    // Drain first. htif_send() waits before writing, but the exit command does
    // not go through it — so without this, exit can overwrite a putchar Spike
    // has not consumed yet and the last character of output is silently lost.
    // Observed: the trailing newline vanished. A reference result whose last
    // byte depends on a race is not a reference result.
    while (tohost != 0)
        fromhost = 0;

    while (1)
        tohost = ((uint64_t)code << 1) | 1;
}
