#include "output.h"
#include "htif.h"

extern volatile uint64_t tohost, fromhost;

static char text[4096];
static uint32_t used;

// The syscall proxy reads eight 64-bit words at the address it is given: the call number, then
// its arguments (fesvr/syscall.cc:448-460). It answers through fromhost once the call is done, and
// puts the call's result in word 0 (:194-207). riscv-tests' benchmarks call it the same way
// (benchmarks/common/syscalls.c:20-36).
static volatile uint64_t magic_mem[8] __attribute__((aligned(64)));

static uint32_t sys_write(const char *p, uint32_t n)
{
    magic_mem[0] = 64;  // SYS_write
    magic_mem[1] = 1;   // the host's standard output
    magic_mem[2] = (uintptr_t)p;
    magic_mem[3] = n;
    __sync_synchronize();
    while (tohost != 0)
        ;
    // Device 0, command 0, payload the address. The upper word is zero, so no half-written value
    // that Spike could read is a different command.
    tohost = (uintptr_t)magic_mem;
    while (fromhost == 0)
        ;
    fromhost = 0;
    __sync_synchronize();
    return (uint32_t)magic_mem[0];
}

void out_flush(void)
{
    if (used && sys_write(text, used) != used)
        htif_exit(5);
    used = 0;
}

void out_char(char c)
{
    if (used == sizeof text)
        out_flush();
    text[used++] = c;
}

void out_str(const char *s)
{
    while (*s)
        out_char(*s++);
}

void out_u32(uint32_t v)
{
    char d[10];
    int n = 0;
    do {
        d[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (n)
        out_char(d[--n]);
}

void out_i32(int32_t v)
{
    if (v < 0) {
        out_char('-');
        out_u32(0u - (uint32_t)v);  // also right for the most negative value
    } else {
        out_u32((uint32_t)v);
    }
}

// Without 64-bit division: there is no libgcc here to provide it.
static const uint64_t power[20] = {
    1ull, 10ull, 100ull, 1000ull, 10000ull, 100000ull, 1000000ull, 10000000ull, 100000000ull,
    1000000000ull, 10000000000ull, 100000000000ull, 1000000000000ull, 10000000000000ull,
    100000000000000ull, 1000000000000000ull, 10000000000000000ull, 100000000000000000ull,
    1000000000000000000ull, 10000000000000000000ull,
};

void out_u64(uint64_t v)
{
    int i = 19;
    while (i > 0 && v < power[i])
        i--;
    for (; i >= 0; i--) {
        char d = '0';
        while (v >= power[i]) {
            v -= power[i];
            d++;
        }
        out_char(d);
    }
}

void out_hex(const uint8_t *p, uint32_t nibbles)
{
    for (uint32_t i = nibbles & 1, end = i + nibbles; i < end; i++) {
        uint32_t b = p[i / 2];
        out_char("0123456789abcdef"[i & 1 ? b & 15 : b >> 4]);
    }
}
