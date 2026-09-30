// What each way of printing costs under Spike. Measured for decisions/0014,
// which decides how the reference decoder's records leave Spike. Not a
// reference program, and not part of the benchmark.
//
// Spike's host side reads tohost once every INTERLEAVE = 5,000 instructions
// (riscv/sim.h:104, riscv/sim.cc:202-219). A program that waits for the host
// to take a command spins until then, and every instruction of the spin
// retires. So one command can cost up to 5,000 instructions, whatever it
// carries.
//
//   MODE_PUTCHAR  N characters, one console command each (htif.c)
//   MODE_WRITE    N characters through the syscall proxy's SYS_write, CHUNK
//                 characters a command (fesvr/syscall.cc:240-246)
//   MODE_COMPUTE  N iterations of a loop with no HTIF traffic: Spike's speed
//
// Each mode prints its count over the loop, last. The printing modes print the
// same N characters first, and `make htif-cost` checks that they do.

#include <stdint.h>
#include "htif.h"

#ifndef N
#error "state the size: build with -DN=<characters or iterations>"
#endif
#ifndef CHUNK
#define CHUNK 1u
#endif

extern volatile uint64_t tohost, fromhost;

static inline uint32_t rd_instret(void)
{
    uint32_t v;
    __asm__ volatile ("rdinstret %0" : "=r"(v));
    return v;
}

#if defined(MODE_PUTCHAR) || defined(MODE_WRITE)
static char text[N];
#endif

#if defined(MODE_WRITE)
// The syscall proxy reads eight 64-bit words at the address it is given:
// the call number, then its arguments (fesvr/syscall.cc:448-460). It answers
// through fromhost once the call is done (:194-206), and puts the call's
// result in word 0. riscv-tests' benchmarks call it the same way
// (benchmarks/common/syscalls.c:20-36).
static volatile uint64_t magic_mem[8] __attribute__((aligned(64)));

static uint32_t sys_write(const char *p, uint32_t len)
{
    magic_mem[0] = 64;              // SYS_write
    magic_mem[1] = 1;               // the host's stdout
    magic_mem[2] = (uintptr_t)p;
    magic_mem[3] = len;
    __sync_synchronize();
    while (tohost != 0)
        ;
    // Device 0, command 0, payload the address. The upper word is zero, so
    // no half-written value that Spike could read is a different command.
    tohost = (uintptr_t)magic_mem;
    while (fromhost == 0)
        ;
    fromhost = 0;
    __sync_synchronize();
    return (uint32_t)magic_mem[0];
}
#endif

int main(void)
{
#if defined(MODE_PUTCHAR) || defined(MODE_WRITE)
    for (uint32_t i = 0; i < N; i++)
        text[i] = (i % 64 == 63) ? '\n' : (char)('a' + i % 26);
#endif

    uint32_t t0 = rd_instret();
#if defined(MODE_PUTCHAR)
    for (uint32_t i = 0; i < N; i++)
        htif_putchar(text[i]);
#elif defined(MODE_WRITE)
    for (uint32_t done = 0; done < N; done += CHUNK) {
        uint32_t n = (N - done < CHUNK) ? N - done : CHUNK;
        if (sys_write(text + done, n) != n)
            htif_exit(3);
    }
#elif defined(MODE_COMPUTE)
    uint32_t acc = 0;
    for (uint32_t i = 0; i < N; i++) {
        acc = (acc << 1) ^ i;
        __asm__ volatile ("" : "+r"(acc));
    }
#else
#error "state the mode: MODE_PUTCHAR, MODE_WRITE or MODE_COMPUTE"
#endif
    uint32_t t1 = rd_instret();

#if defined(MODE_COMPUTE)
    htif_puts("acc      = 0x"); htif_puthex32(acc); htif_putchar('\n');
#endif
    htif_puts("instret  = "); htif_puthex32(t1 - t0); htif_putchar('\n');
    return 0;
}
