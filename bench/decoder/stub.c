// A placeholder decoder, to test the harness before the reference decoder exists. It decodes
// nothing. For each chunk it records where the chunk starts in its connection's stream, and every
// byte the chunk carries. When the input ends, it records each connection's length. expect.py
// predicts every line it prints from stimulus.bin alone.
//
// Its instruction count measures this file, not decoding. Never quote it.

#include "decoder.h"
#include "records.h"

const char decoder_detection[] = "none";

struct conn {
    uint32_t protocol;
    uint32_t at;  // bytes of the connection's stream seen so far
};

static struct conn *conns;
static uint32_t nconns;

uint32_t decoder_memory(uint32_t connections)
{
    return connections * (uint32_t)sizeof(struct conn);
}

void decoder_init(void *memory, uint32_t connections, const uint8_t *protocols)
{
    conns = memory;
    nconns = connections;
    for (uint32_t c = 0; c < connections; c++) {
        conns[c].protocol = protocols[c];
        conns[c].at = 0;
    }
}

// Fields are written out of name order, so that the formatter has to sort them.
static void record_chunk(uint32_t conn, uint32_t protocol, const uint8_t *p, uint32_t n)
{
    struct conn *s = &conns[conn];
    uint32_t *r = rec_open(7 + (n + 3) / 4, TYPE_NONE, protocol, ST_STUB);
    if (r) {
        uint32_t *w = rec_u32(r + 2, F_LEN, n);
        w = rec_hex(w, F_BYTES, p, 2 * n);
        w = rec_u32(w, F_AT, s->at);
        rec_close(r, w, conn);
    }
    s->at += n;
}

// Each protocol has its own path and names its own protocol, so a wrong dispatch prints the wrong
// protocol.
static void gt06_chunk(uint32_t conn, const uint8_t *p, uint32_t n)
{
    record_chunk(conn, PROTO_GT06, p, n);
}

static void jt808_chunk(uint32_t conn, const uint8_t *p, uint32_t n)
{
    record_chunk(conn, PROTO_JT808, p, n);
}

void decoder_chunk(uint32_t conn, const uint8_t *p, uint32_t n)
{
    if (conns[conn].protocol == PROTO_GT06)
        gt06_chunk(conn, p, n);
    else
        jt808_chunk(conn, p, n);
}

void decoder_end(void)
{
    for (uint32_t c = 0; c < nconns; c++) {
        uint32_t *r = rec_open(6, TYPE_NONE, conns[c].protocol, ST_STUB);
        if (r) {
            uint32_t *w = rec_u32(r + 2, F_AT, conns[c].at);
            w = rec_u32(w, F_LEN, 0);
            rec_close(r, w, c);
        }
    }
}
