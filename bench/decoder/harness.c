// The reference decoder's harness (decisions/0014). stimulus.bin is linked into this image. The
// harness checks it, sets up each connection, and counts the decoder's work over the window. After
// the window, it sorts the records into canonical order, formats them and prints them.
//
// Exit codes: 2 the stimulus is refused, 3 memory runs out, 4 a record is malformed in the buffer,
// 5 the host refuses a write (output.c), 6 a trap.

#include <stdint.h>
#include "decoder.h"
#include "htif.h"
#include "output.h"
#include "records.h"

#ifndef MEM_TOP
#error "state where memory ends: build with -DMEM_TOP=<address>"
#endif

extern const uint8_t stimulus[];  // stimulus.S: the file's bytes, after every section of the decoder

uint32_t *rec_next;
uint32_t *rec_limit;
uint32_t rec_full;

typedef uint32_t __attribute__((may_alias)) word;  // so a chunk header is one load

struct header {
    uint32_t chunks, connections, payload;
    const uint8_t *protocols;  // the table: one code for each connection
    const uint8_t *first;      // the first chunk's header
    const uint8_t *end;        // the byte after the last chunk
};

static uint32_t le16(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8; }
static uint32_t le32(const uint8_t *p) { return le16(p) | le16(p + 2) << 16; }

// Before the window: what bench/stimulus/container.py's unpack() refuses, refused here too. The
// file's length cannot be checked here, because no code may depend on the stimulus's size (0014,
// section 1). The Makefile holds the linked file to its manifest.json's hash instead.
static const char *check(const uint8_t *s, struct header *h)
{
    if (s[0] != 'T' || s[1] != 'F' || s[2] != 'D' || s[3] != 'S')
        return "it does not start with TFDS";
    if (le16(s + 4) != 2)
        return "it is not format version 2";
    if (le16(s + 6) != 20)
        return "its header is not 20 bytes";
    h->chunks = le32(s + 8);
    h->connections = le32(s + 12);
    h->payload = le32(s + 16);
    if (h->connections == 0 || h->connections > 0x10000)
        return "its number of connections is out of range";
    h->protocols = s + 20;
    for (uint32_t c = 0; c < h->connections; c++)
        if (h->protocols[c] != PROTO_GT06 && h->protocols[c] != PROTO_JT808)
            return "a protocol code is neither 1 nor 2";
    const uint8_t *p = h->protocols + h->connections;
    for (; (p - s) % 4; p++)
        if (*p)
            return "the padding after the table is not zero";
    h->first = p;
    uint32_t payload = 0;
    for (uint32_t i = 0; i < h->chunks; i++) {
        uint32_t n = le16(p), conn = le16(p + 2);
        if (n == 0 || conn >= h->connections)
            return "a chunk header is bad";
        p += 4 + n;
        for (; (p - s) % 4; p++)
            if (*p)
                return "the padding after a chunk is not zero";
        payload += n;
    }
    if (payload != h->payload)
        return "the chunks do not add up to the header's payload bytes";
    h->end = p;
    return 0;
}

// All 64 bits. The low half alone wraps after 4,294,967,296 instructions (0014, section 3).
static inline uint64_t instret(void)
{
    uint32_t hi, lo, again;
    do {
        __asm__ volatile ("rdinstreth %0" : "=r"(hi) :: "memory");
        __asm__ volatile ("rdinstret %0" : "=r"(lo) :: "memory");
        __asm__ volatile ("rdinstreth %0" : "=r"(again) :: "memory");
    } while (hi != again);
    return (uint64_t)hi << 32 | lo;
}

// --- After the window: the formatter. It turns values into text and does nothing else (0014,
// section 4). What it refuses is a record that records.h could not have written.

enum kind { U32, I32, U64, HEX };

static const struct {
    char name[13];
    uint8_t kind;
} fields[F_COUNT] = {
    [F_ADC1] = {"adc1", U32},         [F_ADC2] = {"adc2", U32},
    [F_ALARM] = {"alarm", U32},       [F_ALTITUDE] = {"altitude", I32},
    [F_ARCHIVE] = {"archive", U32},   [F_AT] = {"at", U32},
    [F_BATTERY] = {"battery", U32},   [F_BYTES] = {"bytes", HEX},
    [F_CID] = {"cid", U32},           [F_COURSE] = {"course", U32},
    [F_DEVICE] = {"device", HEX},     [F_DIFFERENTIAL] = {"differential", U32},
    [F_FUEL] = {"fuel", U32},         [F_GSM] = {"gsm", U32},
    [F_HEADER] = {"header", U32},     [F_INDEX] = {"index", U32},
    [F_INFO] = {"info", U32},         [F_INPUTS] = {"inputs", U32},
    [F_LAC] = {"lac", U32},           [F_LANGUAGE] = {"language", U32},
    [F_LAT] = {"lat", I32},           [F_LEN] = {"len", U32},
    [F_LON] = {"lon", I32},           [F_MCC] = {"mcc", U32},
    [F_MNC] = {"mnc", U32},           [F_ODOMETER] = {"odometer", U64},
    [F_PRODUCT] = {"product", U32},   [F_RECORD] = {"record", U32},
    [F_RSSI] = {"rssi", U32},         [F_SATELLITES] = {"satellites", U32},
    [F_SERIAL] = {"serial", U32},     [F_SPEED] = {"speed", U32},
    [F_STATUS] = {"status", U32},     [F_TEXT] = {"text", HEX},
    [F_TIME] = {"time", U32},         [F_VALID] = {"valid", U32},
    [F_VOLTAGE] = {"voltage", U32},
};

static const char *const status_name[] = {
    [ST_OK] = "ok", [ST_CRC_FAIL] = "crc_fail", [ST_MALFORMED] = "malformed",
    [ST_RESYNC] = "resync", [ST_UNSUPPORTED] = "unsupported", [ST_SENT] = "sent",
    [ST_STUB] = "stub",
};

static const char *const protocol_name[] = {[PROTO_GT06] = "gt06", [PROTO_JT808] = "jt808"};

#define MAX_FIELDS 48

static uint32_t field_words(uint32_t head)
{
    switch (fields[head & 0xFF].kind) {
    case HEX:
        return 1 + (((head >> 16) + 1) / 2 + 3) / 4;
    case U64:
        return 3;
    default:
        return 2;
    }
}

// Prints one record. Returns 0, or what is wrong with it.
static const char *put_record(const uint32_t *r)
{
    uint32_t words = r[0] & 0xFFFF, conn = r[0] >> 16;
    uint32_t type = r[1] & 0xFFFF, protocol = r[1] >> 16 & 0xFF, status = r[1] >> 24;
    if (protocol != PROTO_GT06 && protocol != PROTO_JT808)
        return "a protocol code";
    if (status > ST_STUB)
        return "a status code";
    if (protocol == PROTO_GT06 && type > 0xFF && type < TYPE_SENTENCE)
        return "a GT06 type above 0xff";

    const uint32_t *f[MAX_FIELDS];
    uint32_t n = 0;
    const uint32_t *w = r + 2, *end = r + words;
    while (w < end) {
        uint32_t id = w[0] & 0xFF;
        if (id >= F_COUNT || n == MAX_FIELDS)
            return "a field id, or too many fields";
        if (w[0] & 0xFF00 || (fields[id].kind != HEX && w[0] >> 16))
            return "a field header";
        f[n++] = w;
        w += field_words(w[0]);
    }
    if (w != end)
        return "fields that overrun their record";

    // Sorting by id sorts by name. Insertion sort is stable, so a repeated field keeps its order.
    for (uint32_t i = 1; i < n; i++) {
        const uint32_t *x = f[i];
        uint32_t j = i;
        for (; j && (f[j - 1][0] & 0xFF) > (x[0] & 0xFF); j--)
            f[j] = f[j - 1];
        f[j] = x;
    }

    out_u32(conn);
    out_char(' ');
    out_str(protocol_name[protocol]);
    out_char(' ');
    if (type == TYPE_NONE)
        out_char('-');
    else if (type == TYPE_SENTENCE)
        out_str("sentence");
    else
        for (int i = protocol == PROTO_GT06 ? 4 : 12; i >= 0; i -= 4)
            out_char("0123456789abcdef"[type >> i & 15]);
    out_char(' ');
    out_str(status_name[status]);
    for (uint32_t i = 0; i < n; i++) {
        const uint32_t *x = f[i];
        uint32_t id = x[0] & 0xFF;
        out_char(' ');
        out_str(fields[id].name);
        out_char('=');
        switch (fields[id].kind) {
        case U32:
            out_u32(x[1]);
            break;
        case I32:
            out_i32((int32_t)x[1]);
            break;
        case U64:
            out_u64((uint64_t)x[2] << 32 | x[1]);
            break;
        default:
            out_hex((const uint8_t *)(x + 1), x[0] >> 16);
        }
    }
    out_char('\n');
    return 0;
}

static void put_key(const char *key)
{
    uint32_t n = 0;
    for (; key[n]; n++)
        out_char(key[n]);
    for (; n < 12; n++)
        out_char(' ');
    out_str("= ");
}

static void put_line(const char *key, uint32_t value)
{
    put_key(key);
    out_u32(value);
    out_char('\n');
}

// Any trap ends the run. No measured window may include a trap that the configuration does not
// declare (decisions/0009), and nothing here could resume after one. Without this, a trap jumps to
// whatever mtvec holds, and Spike runs until someone stops it: a mutation of the chunk walk did.
// It reads only mcause and mepc, which are in 0009's minimum. mtval is still an open item there.
#define CSR(insn) ".option push\n.option arch, +zicsr\n" insn "\n.option pop"

static void __attribute__((noreturn, aligned(4))) trap(void)
{
    uint32_t cause, epc;
    __asm__ volatile (CSR("csrr %0, mcause") : "=r"(cause));
    __asm__ volatile (CSR("csrr %0, mepc") : "=r"(epc));
    uint8_t pc[4] = {epc >> 24, epc >> 16, epc >> 8, epc};
    out_str("trap: mcause ");
    out_u32(cause);
    out_str(", mepc 0x");
    out_hex(pc, 8);
    out_char('\n');
    out_flush();
    htif_exit(6);
}

static int fail(int code, const char *what, const char *why)
{
    out_str(what);
    out_str(why);
    out_char('\n');
    out_flush();
    return code;
}

int main(void)
{
    __asm__ volatile (CSR("csrw mtvec, %0") :: "r"(trap));

    struct header h;
    const char *why = check(stimulus, &h);
    if (why)
        return fail(2, "stimulus refused: ", why);

    // Memory from the end of the stimulus to MEM_TOP: each connection's state, then the records.
    uintptr_t at = ((uintptr_t)h.end + 15) & ~(uintptr_t)15;
    uintptr_t records = (at + decoder_memory(h.connections) + 15) & ~(uintptr_t)15;
    if (records + 4096 > (uintptr_t)MEM_TOP)
        return fail(3, "out of memory: ", "the stimulus and the state leave no room for records");
    decoder_init((void *)at, h.connections, h.protocols);
    uint32_t *base = (uint32_t *)records;
    rec_next = base;
    rec_limit = (uint32_t *)MEM_TOP;

    // The window (0014, section 3): the walk over the chunks, the decoder, and the end of input.
    const uint8_t *p = h.first;
    uint64_t t0 = instret();
    for (uint32_t i = h.chunks; i; i--) {
        uint32_t w = *(const word *)p;  // u16 length | u16 connection
        uint32_t n = w & 0xFFFF;
        decoder_chunk(w >> 16, p + 4, n);
        p += 4 + ((n + 3) & ~3u);
    }
    decoder_end();
    uint64_t t1 = instret();

    if (rec_full)
        return fail(3, "out of memory: ", "a record did not fit in the record buffer");

    // Canonical order (0012, section 7): a stable counting sort by connection.
    uint32_t *count = rec_next, *index = count + h.connections, total = 0;
    for (const uint32_t *r = base; r < rec_next; r += r[0] & 0xFFFF) {
        if ((r[0] & 0xFFFF) < 2 || r + (r[0] & 0xFFFF) > rec_next || r[0] >> 16 >= h.connections)
            return fail(4, "record buffer: ", "a record's length or connection is out of range");
        total++;
    }
    if ((uintptr_t)(index + total) > (uintptr_t)MEM_TOP)
        return fail(3, "out of memory: ", "no room to sort the records");
    for (uint32_t c = 0; c < h.connections; c++)
        count[c] = 0;
    for (const uint32_t *r = base; r < rec_next; r += r[0] & 0xFFFF)
        count[r[0] >> 16]++;
    for (uint32_t c = 0, start = 0; c < h.connections; c++) {
        uint32_t n = count[c];
        count[c] = start;
        start += n;
    }
    for (const uint32_t *r = base; r < rec_next; r += r[0] & 0xFFFF)
        index[count[r[0] >> 16]++] = (uint32_t)(r - base);

    // What each run prints (0014, section 6).
    put_line("format", 2);
    put_line("chunks", h.chunks);
    put_line("connections", h.connections);
    put_line("payload", h.payload);
    put_key("detection");
    out_str(decoder_detection);
    out_char('\n');
    put_key("instret");
    out_u64(t1 - t0);
    out_char('\n');
    put_line("records", total);
    for (uint32_t i = 0; i < total; i++) {
        why = put_record(base + index[i]);
        if (why)
            return fail(4, "record buffer: malformed ", why);
    }
    put_line("end", total);
    out_flush();
    return 0;
}
