// A test decoder for the formatter. It ignores the stimulus. When the input ends, it appends ten
// records that use every field name, every kind of value at its extremes, every status, and every
// form of type. format_test.expected holds the text they must print, written out by hand from
// SPEC §3. The records name their connections out of order, so the sort is tested too. They name
// connections 0 to 11, so the stimulus must have at least 12, as the coverage stimulus does.
//
// Its instruction count measures nothing. Never quote it.

#include "decoder.h"
#include "records.h"

const char decoder_detection[] = "none";

uint32_t decoder_memory(uint32_t connections)
{
    (void)connections;
    return 0;
}

void decoder_init(void *memory, uint32_t connections, const uint8_t *protocols)
{
    (void)memory;
    (void)connections;
    (void)protocols;
}

void decoder_chunk(uint32_t conn, const uint8_t *p, uint32_t n)
{
    (void)conn;
    (void)p;
    (void)n;
}

static const uint8_t imei[8] = {0x01, 0x23, 0x45, 0x67, 0x89, 0x01, 0x23, 0x45};
static const uint8_t reply[10] = {0x78, 0x78, 0x05, 0x01, 0x00, 0x01, 0xd9, 0xdc, 0x0d, 0x0a};
static const uint8_t id_2013[6] = {0x00, 0x00, 0x00, 0x51, 0x85, 0x30};
static const uint8_t id_2019[10] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x51, 0x85, 0x30};
static const uint8_t two_letters[2] = {0x41, 0x42};
static const uint8_t three_digits[2] = {0x0a, 0xbc};

void decoder_end(void)
{
    uint32_t *r, *w;

    // 1. Every field once, written in reverse order of name.
    if (!(r = rec_open(128, 0x12, PROTO_GT06, ST_OK)))
        return;
    w = rec_u32(r + 2, F_VOLTAGE, 7);
    w = rec_u32(w, F_VALID, 1);
    w = rec_u32(w, F_TIME, 1790000000u);
    w = rec_hex(w, F_TEXT, two_letters, 4);
    w = rec_u32(w, F_STATUS, 4294967295u);
    w = rec_u32(w, F_SPEED, 0);
    w = rec_u32(w, F_SERIAL, 65535);
    w = rec_u32(w, F_SATELLITES, 12);
    w = rec_u32(w, F_RSSI, 31);
    w = rec_u32(w, F_RECORD, 1);
    w = rec_u32(w, F_PRODUCT, 255);
    w = rec_u64(w, F_ODOMETER, 18446744073709551615ull);
    w = rec_u32(w, F_MNC, 0);
    w = rec_u32(w, F_MCC, 460);
    w = rec_u32(w, F_LON, (uint32_t)INT32_MAX);
    w = rec_u32(w, F_LEN, 18);
    w = rec_u32(w, F_LAT, (uint32_t)INT32_MIN);
    w = rec_u32(w, F_LANGUAGE, 2);
    w = rec_u32(w, F_LAC, 65535);
    w = rec_u32(w, F_INPUTS, 4096);
    w = rec_u32(w, F_INFO, 68);
    w = rec_u32(w, F_INDEX, 0);
    w = rec_u32(w, F_HEADER, 2019);
    w = rec_u32(w, F_GSM, 4);
    w = rec_u32(w, F_FUEL, 100);
    w = rec_u32(w, F_DIFFERENTIAL, 0);
    w = rec_hex(w, F_DEVICE, imei, 15);
    w = rec_u32(w, F_COURSE, 359);
    w = rec_u32(w, F_CID, 16777215);
    w = rec_hex(w, F_BYTES, reply, 20);
    w = rec_u32(w, F_BATTERY, 100);
    w = rec_u32(w, F_AT, 0);
    w = rec_u32(w, F_ARCHIVE, 1);
    w = rec_u32(w, F_ALTITUDE, (uint32_t)-1);
    w = rec_u32(w, F_ALARM, 2147483648u);
    w = rec_u32(w, F_ADC2, 1);
    w = rec_u32(w, F_ADC1, 0);
    rec_close(r, w, 3);

    // 2. A u64 just past 32 bits, a negative one, and zero.
    if (!(r = rec_open(16, 0x0200, PROTO_JT808, ST_OK)))
        return;
    w = rec_u64(r + 2, F_ODOMETER, 4294967296ull);
    w = rec_u32(w, F_LAT, (uint32_t)-1);
    w = rec_hex(w, F_DEVICE, id_2013, 12);
    w = rec_u32(w, F_TIME, 0);
    rec_close(r, w, 11);

    // 3. A second record for connection 3: it must stay after the first.
    if (!(r = rec_open(8, 0x01, PROTO_GT06, ST_SENT)))
        return;
    w = rec_hex(r + 2, F_BYTES, reply, 20);
    rec_close(r, w, 3);

    // 4. An empty hex value, and 20 digits.
    if (!(r = rec_open(8, TYPE_SENTENCE, PROTO_JT808, ST_OK)))
        return;
    w = rec_hex(r + 2, F_TEXT, two_letters, 0);
    w = rec_hex(w, F_DEVICE, id_2019, 20);
    rec_close(r, w, 0);

    // 5. The largest u32 in a field that only ever holds small ones.
    if (!(r = rec_open(6, TYPE_NONE, PROTO_JT808, ST_RESYNC)))
        return;
    w = rec_u32(r + 2, F_LEN, 1);
    w = rec_u32(w, F_AT, 4294967295u);
    rec_close(r, w, 0);

    // 6. A GT06 type with a letter in it.
    if (!(r = rec_open(6, 0x3a, PROTO_GT06, ST_UNSUPPORTED)))
        return;
    w = rec_u32(r + 2, F_AT, 7);
    w = rec_u32(w, F_LEN, 21);
    rec_close(r, w, 5);

    // 7. A JT808 type with a leading zero.
    if (!(r = rec_open(6, 0x0f0a, PROTO_JT808, ST_CRC_FAIL)))
        return;
    w = rec_u32(r + 2, F_AT, 1);
    w = rec_u32(w, F_LEN, 2);
    rec_close(r, w, 7);

    // 8. An odd number of digits other than an IMEI's 15.
    if (!(r = rec_open(4, 0x8001, PROTO_JT808, ST_SENT)))
        return;
    w = rec_hex(r + 2, F_BYTES, three_digits, 3);
    rec_close(r, w, 7);

    // 9. malformed, which no fault that the generator makes produces today (0011).
    if (!(r = rec_open(6, 0x13, PROTO_GT06, ST_MALFORMED)))
        return;
    w = rec_u32(r + 2, F_AT, 0);
    w = rec_u32(w, F_LEN, 15);
    rec_close(r, w, 9);

    // 10. A record with no fields at all.
    if (!(r = rec_open(2, TYPE_NONE, PROTO_JT808, ST_STUB)))
        return;
    rec_close(r, r + 2, 2);
}
