// The record buffer: how a decoder hands each record on, inside the measured window
// (decisions/0014, section 4). A record is a value. After the window, the formatter turns it into
// SPEC §3's text, and does nothing else.
//
// A record is a run of 32-bit words:
//
//   word 0   words in the record, this one included | connection << 16
//   word 1   type | protocol << 16 | status << 24
//   fields   in any order, each one a header word and then its value:
//            a number      id                 | the value: 1 word, or 2 for a u64, low word first
//            hex digits    id | nibbles << 16 | (nibbles + 1) / 2 bytes, zero-padded to a word
//
// A field's id fixes its kind, so a value carries no type of its own. The ids follow the
// alphabetical order of the names, so sorting fields by id sorts them by name, as SPEC §3 requires.

#ifndef RECORDS_H
#define RECORDS_H
#include <stdint.h>

enum protocol { PROTO_GT06 = 1, PROTO_JT808 = 2 };  // the codes in stimulus.bin's table
enum status { ST_OK, ST_CRC_FAIL, ST_MALFORMED, ST_RESYNC, ST_UNSUPPORTED, ST_SENT, ST_STUB };
enum { TYPE_NONE = 0xFFFF, TYPE_SENTENCE = 0xFFFE };  // printed as "-" and as "sentence"

enum field {
    F_ADC1, F_ADC2, F_ALARM, F_ALTITUDE, F_ARCHIVE, F_AT, F_BATTERY, F_BYTES, F_CID, F_COURSE,
    F_DEVICE, F_DIFFERENTIAL, F_FUEL, F_GSM, F_HEADER, F_INDEX, F_INFO, F_INPUTS, F_LAC,
    F_LANGUAGE, F_LAT, F_LEN, F_LON, F_MCC, F_MNC, F_ODOMETER, F_PRODUCT, F_RECORD, F_RSSI,
    F_SATELLITES, F_SERIAL, F_SPEED, F_STATUS, F_TEXT, F_TIME, F_VALID, F_VOLTAGE, F_COUNT
};

extern uint32_t *rec_next;   // where the next record starts
extern uint32_t *rec_limit;  // the first word past the buffer
extern uint32_t rec_full;    // set when a record does not fit. The run then fails.

// Opens a record of at most `words` words. If it does not fit, sets rec_full and returns 0.
static inline uint32_t *rec_open(uint32_t words, uint32_t type, uint32_t protocol, uint32_t status)
{
    uint32_t *r = rec_next;
    if ((uint32_t)(rec_limit - r) < words) {
        rec_full = 1;
        return 0;
    }
    r[1] = type | protocol << 16 | status << 24;
    return r;
}

// Each field writer stores at w, and returns the word after the field.
static inline uint32_t *rec_u32(uint32_t *w, uint32_t id, uint32_t value)
{
    w[0] = id;
    w[1] = value;
    return w + 2;
}

static inline uint32_t *rec_u64(uint32_t *w, uint32_t id, uint64_t value)
{
    w[0] = id;
    w[1] = (uint32_t)value;
    w[2] = (uint32_t)(value >> 32);
    return w + 3;
}

// The last `nibbles` hex digits of the (nibbles + 1) / 2 bytes at p. So 15 digits of 8 BCD bytes
// drop the first digit, as a GT06 login's IMEI does (SPEC §3).
static inline uint32_t *rec_hex(uint32_t *w, uint32_t id, const uint8_t *p, uint32_t nibbles)
{
    uint32_t n = (nibbles + 1) / 2;
    uint8_t *b = (uint8_t *)(w + 1);
    w[0] = id | nibbles << 16;
    for (uint32_t i = 0; i < n; i++)
        b[i] = p[i];
    for (uint32_t i = n; i % 4; i++)
        b[i] = 0;
    return w + 1 + (n + 3) / 4;
}

// Closes the record that rec_open returned as r, whose fields end at w.
static inline void rec_close(uint32_t *r, uint32_t *w, uint32_t conn)
{
    r[0] = (uint32_t)(w - r) | conn << 16;
    rec_next = w;
}

#endif
