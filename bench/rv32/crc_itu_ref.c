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
//
// decisions/0008: the source states the algorithm and the work, and the
// compiler may substitute neither. Two forms of the same CRC, chosen at build
// time with CRC_IMPL (bench/rv32/Makefile):
//
//   table    THE REFERENCE. The byte-wise reflected table: one lookup per byte.
//   bitwise  The definition: eight shift-and-conditional-xor steps per byte.
//            Kept as the specification form and as the subject of experiments
//            on what compilers and ISAs do with it. Never quoted as the
//            reference.
//
// Both print identical reference lines, and crc_oracle.py checks either.

#include <stdint.h>
#include "htif.h"

#define ITERS 1000u

// The CRC-covered region of a GT06 login frame (protocol 0x01):
//   len  proto  terminal id (8, synthetic)            serial
static uint8_t frame[12] = {
    0x0D, 0x01, 0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0x00, 0x01
};

#if defined(CRC_IMPL_table)

// Entry i is the bitwise definition below applied to the single byte i:
//   for i in range(256): c = i; repeat 8: c = (c >> 1) ^ 0x8408 if c & 1 else c >> 1
// The sweep in main uses all 256 indices, so a wrong entry changes acc and
// fails `make check`. Identical, entry for entry, to crctab16 in the GT06
// protocol document v1.8.1, Appendix A (pinned in reference/README.md).
// GetCrc16 there is the loop below.
static const uint16_t crc_itu_table[256] = {
    0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
    0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7,
    0x1081, 0x0108, 0x3393, 0x221A, 0x56A5, 0x472C, 0x75B7, 0x643E,
    0x9CC9, 0x8D40, 0xBFDB, 0xAE52, 0xDAED, 0xCB64, 0xF9FF, 0xE876,
    0x2102, 0x308B, 0x0210, 0x1399, 0x6726, 0x76AF, 0x4434, 0x55BD,
    0xAD4A, 0xBCC3, 0x8E58, 0x9FD1, 0xEB6E, 0xFAE7, 0xC87C, 0xD9F5,
    0x3183, 0x200A, 0x1291, 0x0318, 0x77A7, 0x662E, 0x54B5, 0x453C,
    0xBDCB, 0xAC42, 0x9ED9, 0x8F50, 0xFBEF, 0xEA66, 0xD8FD, 0xC974,
    0x4204, 0x538D, 0x6116, 0x709F, 0x0420, 0x15A9, 0x2732, 0x36BB,
    0xCE4C, 0xDFC5, 0xED5E, 0xFCD7, 0x8868, 0x99E1, 0xAB7A, 0xBAF3,
    0x5285, 0x430C, 0x7197, 0x601E, 0x14A1, 0x0528, 0x37B3, 0x263A,
    0xDECD, 0xCF44, 0xFDDF, 0xEC56, 0x98E9, 0x8960, 0xBBFB, 0xAA72,
    0x6306, 0x728F, 0x4014, 0x519D, 0x2522, 0x34AB, 0x0630, 0x17B9,
    0xEF4E, 0xFEC7, 0xCC5C, 0xDDD5, 0xA96A, 0xB8E3, 0x8A78, 0x9BF1,
    0x7387, 0x620E, 0x5095, 0x411C, 0x35A3, 0x242A, 0x16B1, 0x0738,
    0xFFCF, 0xEE46, 0xDCDD, 0xCD54, 0xB9EB, 0xA862, 0x9AF9, 0x8B70,
    0x8408, 0x9581, 0xA71A, 0xB693, 0xC22C, 0xD3A5, 0xE13E, 0xF0B7,
    0x0840, 0x19C9, 0x2B52, 0x3ADB, 0x4E64, 0x5FED, 0x6D76, 0x7CFF,
    0x9489, 0x8500, 0xB79B, 0xA612, 0xD2AD, 0xC324, 0xF1BF, 0xE036,
    0x18C1, 0x0948, 0x3BD3, 0x2A5A, 0x5EE5, 0x4F6C, 0x7DF7, 0x6C7E,
    0xA50A, 0xB483, 0x8618, 0x9791, 0xE32E, 0xF2A7, 0xC03C, 0xD1B5,
    0x2942, 0x38CB, 0x0A50, 0x1BD9, 0x6F66, 0x7EEF, 0x4C74, 0x5DFD,
    0xB58B, 0xA402, 0x9699, 0x8710, 0xF3AF, 0xE226, 0xD0BD, 0xC134,
    0x39C3, 0x284A, 0x1AD1, 0x0B58, 0x7FE7, 0x6E6E, 0x5CF5, 0x4D7C,
    0xC60C, 0xD785, 0xE51E, 0xF497, 0x8028, 0x91A1, 0xA33A, 0xB2B3,
    0x4A44, 0x5BCD, 0x6956, 0x78DF, 0x0C60, 0x1DE9, 0x2F72, 0x3EFB,
    0xD68D, 0xC704, 0xF59F, 0xE416, 0x90A9, 0x8120, 0xB3BB, 0xA232,
    0x5AC5, 0x4B4C, 0x79D7, 0x685E, 0x1CE1, 0x0D68, 0x3FF3, 0x2E7A,
    0xE70E, 0xF687, 0xC41C, 0xD595, 0xA12A, 0xB0A3, 0x8238, 0x93B1,
    0x6B46, 0x7ACF, 0x4854, 0x59DD, 0x2D62, 0x3CEB, 0x0E70, 0x1FF9,
    0xF78F, 0xE606, 0xD49D, 0xC514, 0xB1AB, 0xA022, 0x92B9, 0x8330,
    0x7BC7, 0x6A4E, 0x58D5, 0x495C, 0x3DE3, 0x2C6A, 0x1EF1, 0x0F78
};

static uint16_t crc_itu(const uint8_t *p, unsigned n)
{
    uint16_t crc = 0xFFFF;
    for (unsigned i = 0; i < n; i++)
        crc = (uint16_t)((crc >> 8) ^ crc_itu_table[(crc ^ p[i]) & 0xFFu]);
    return (uint16_t)~crc;
}

#elif defined(CRC_IMPL_bitwise)

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

#else
#error "state the CRC form: build with CRC_IMPL=table or CRC_IMPL=bitwise (see decisions/0008)"
#endif

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
        // Each frame arrives as memory the compiler cannot predict, as a real
        // one would. Without this, a compiler that can prove bytes 0..9 never
        // change may hoist their CRC out of the loop. In experiments/0001 one
        // build did a sixth of the declared work that way and still printed
        // every reference line correctly.
        __asm__ volatile ("" ::: "memory");
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
