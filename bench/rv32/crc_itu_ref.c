// CRC-ITU over a GT06-shaped frame — the smallest real piece of the eventual
// Telematics Frame Decoder Benchmark, used here to establish the REFERENCE
// PROCESS before the decoder exists.
//
// Provenance: spec-derived reconstruction. The frame below is synthesised from
// the published GT06 layout; the terminal ID is the obviously-fake sequence
// 01 23 45 67 89 AB CD EF. No captured operational data, no real IMEI.
// See bench/README.md rules 1, 2 and 2a.
//
// CRC-ITU (CRC-16/X-25): poly 0x1021 reflected to 0x8408, init 0xFFFF,
// reflected in and out, final complement. GT06 computes it from the length
// byte through the serial number, excluding the 7878 header and 0D0A trailer.

#include <stdint.h>
#include "htif.h"

#define ITERS 1000u

// The CRC-covered region of a GT06 login frame (protocol 0x01):
//   len  proto  terminal id (8, synthetic)            serial
static uint8_t frame[12] = {
    0x0D, 0x01, 0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0x00, 0x01
};

static uint16_t crc_itu(const uint8_t *p, unsigned n)
{
    uint16_t crc = 0xFFFF;
    for (unsigned i = 0; i < n; i++) {
        crc ^= p[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 1u) ? (uint16_t)((crc >> 1) ^ 0x8408) : (uint16_t)(crc >> 1);
    }
    return (uint16_t)~crc;
}

static inline uint32_t rd_instret(void)
{
    uint32_t v;
    __asm__ volatile ("rdinstret %0" : "=r"(v));
    return v;
}

int main(void)
{
    uint32_t t0 = rd_instret();

    // 1. the reference frame's CRC — one fixed, checkable number
    uint16_t ref = crc_itu(frame, sizeof frame);

    // 2. enough work to be worth counting: sweep the serial field
    uint32_t acc = 0;
    for (unsigned i = 0; i < ITERS; i++) {
        frame[10] = (uint8_t)(i >> 8);
        frame[11] = (uint8_t)(i & 0xFF);
        uint16_t c = crc_itu(frame, sizeof frame);
        acc = (acc << 1) | (acc >> 31);
        acc ^= c;
    }

    uint32_t t1 = rd_instret();

    htif_puts("crc_ref  = 0x"); htif_puthex16(ref); htif_putchar('\n');
    htif_puts("acc      = 0x"); htif_puthex32(acc); htif_putchar('\n');
    htif_puts("iters    = ");   htif_puthex32(ITERS); htif_putchar('\n');
    htif_puts("instret  = ");   htif_puthex32(t1 - t0); htif_putchar('\n');
    return 0;
}
