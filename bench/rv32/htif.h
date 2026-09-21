// Minimal HTIF host interface. There is no libc on this target — homebrew's
// riscv64-elf-gcc ships a freestanding compiler with no newlib — so output and
// exit go straight through Spike's host-target interface.
//
// That is not a workaround, it is the right target for this project: the core
// we are building will have no OS and no libc either, so a reference result
// measured through newlib's printf would be measuring newlib.
#ifndef HTIF_H
#define HTIF_H
#include <stdint.h>

void htif_putchar(int c);
void htif_puts(const char *s);
void htif_puthex16(uint16_t v);
void htif_puthex32(uint32_t v);
void htif_exit(int code) __attribute__((noreturn));

#endif
