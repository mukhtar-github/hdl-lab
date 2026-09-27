"""JT/T 808 frames, laid out from Traccar. Citation keys: see common.py.

No JT/T 808 standard document is pinned in reference/, so every layout here is read from Traccar's
decoder, the de facto documentation (reference/README.md), and cited to its lines. Where Traccar
does not settle a choice, the choice is a rule, listed in README.md.

    delimiter | header | body | check | delimiter           delimiter 0x7E, or 0xE7 "alternative"
    header = type(2) attribute(2) [version(1)] id(6|7|10) index(2|1)     Jt808ProtocolDecoder:359-373
    attribute: body length in bits 0-9 (:363); bit 14 says a version byte follows (:365)
    check = XOR of header and body (:146)
    header, body and check are escaped, the delimiters are not           Jt808FrameDecoder:61-91

A "(" … ")" sentence is framed by its parentheses, with no header, check or escaping
(Jt808FrameDecoder:49-54; Jt808ProtocolDecoder:345-357).
"""

from common import bcd

STANDARD, ALTERNATIVE = 0x7E, 0xE7

# Escaping, as the inverse of Jt808FrameDecoder.java:67-84. The alternative alphabet maps 3E 02 to
# 3D, so 0x3D is escaped too (rule R9): a raw 0x3D would also decode to 0x3D, since only E6 and 3E
# introduce an escape there.
ESCAPE = {
    STANDARD: {0x7D: b"\x7d\x01", 0x7E: b"\x7d\x02"},
    ALTERNATIVE: {0xE6: b"\xe6\x01", 0xE7: b"\xe6\x02", 0x3E: b"\x3e\x01", 0x3D: b"\x3e\x02"},
}

AUTH, LOCATION, BATCH, LOCATION2 = 0x0102, 0x0200, 0x0704, 0x5501  # Jt808ProtocolDecoder:76-84
SHORT_INDEX = (0x5501, 0x5502)  # these two read a 1-byte index, :369-373

# Message types for SPEC §4's unknown message type. The high byte 0x0F appears nowhere in
# Jt808ProtocolDecoder.java as a MSG_ constant, a case label or an == operand.
UNKNOWN = tuple(range(0x0F00, 0x0F10))

# Rule R8: the version byte of a 2019-format header. Traccar reads it and never interprets it
# (:365); the value 1 is not from a pinned source.
VERSION_2019 = 1

# Additional-information items of a location report that Traccar reads, with their lengths:
# 0x01 odometer (:791), 0x02 fuel (:794), 0x25 inputs (:819), 0x2B two ADC words (:822),
# 0x30 RSSI (:827), 0x31 satellites (:830).
ITEMS = {0x01: 4, 0x02: 2, 0x25: 4, 0x2B: 4, 0x30: 1, 0x31: 1}

ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def id_length(delimiter, version_2019):
    """Bytes of terminal ID, :366: 10 when a version byte is present, else 7 after 0xE7, else 6."""
    return 10 if version_2019 else (7 if delimiter == ALTERNATIVE else 6)


def xor(data):
    x = 0
    for b in data:
        x ^= b
    return x


def escape(data, delimiter):
    table = ESCAPE[delimiter]
    return b"".join(table.get(b, bytes([b])) for b in data)


def frame(msg_type, body, *, delimiter, terminal, index, version_2019, flag_lie=False,
          body_length=None, check_error=0):
    """One delimited frame.

    `flag_lie` sets attribute bit 14 on a 2013-format header: no version byte, 6- or 7-byte ID
    (SPEC §4, flag-lying frame). `body_length` replaces the correct body length, and the check is
    then computed over the header actually written, so the length is the only fault. `check_error`
    is XORed into the correct check (SPEC §4, bad checksum). Escaping happens after both."""
    attribute = len(body) if body_length is None else body_length
    if not 0 <= attribute <= 0x3FF:
        raise ValueError(f"body length {attribute} does not fit attribute bits 0-9")
    if version_2019 or flag_lie:
        attribute |= 0x4000
    header = msg_type.to_bytes(2, "big") + attribute.to_bytes(2, "big")
    if version_2019:
        header += bytes([VERSION_2019])
    header += bcd(terminal.rjust(2 * id_length(delimiter, version_2019), "0"))
    header += (index & 0xFF).to_bytes(1, "big") if msg_type in SHORT_INDEX else \
        (index & 0xFFFF).to_bytes(2, "big")
    raw = header + body
    return (bytes([delimiter]) + escape(raw + bytes([xor(raw) ^ check_error]), delimiter)
            + bytes([delimiter]))


# --- Terminal authentication, 0x0102 ----------------------------------------------------------

def auth_fields(rng, length_range):
    """Rule R10: the 2013 body, an authentication code and nothing else, for both formats. Traccar
    never reads this body (:445-448), and the 2019 body has no pinned source."""
    return {"code": "".join(ALNUM[rng.below(len(ALNUM))] for _ in range(rng.between(*length_range)))}


def auth_body(f):
    return f["code"].encode("ascii")


# --- Location report, 0x0200 ------------------------------------------------------------------

def location_fields(rng, time, item_range, forbidden_items_length):
    """decodeLocation, :748-786, and decodeCoordinates, :707-739.

    `forbidden_items_length`: Traccar reads a location whose remainder after the fixed 28 bytes is
    exactly 20 bytes as a vendor format, not as items (:765-775). In a frame the remainder includes
    the check and the closing delimiter, so an 18-byte item block is avoided; inside a batch record
    it is 20 (rule R11). Neither decoder may be handed a frame the other reads differently."""
    f = {
        "alarm": 0 if rng.below(4) else 1 << rng.below(32),  # rule R12
        "acc": rng.between(0, 1),               # status bit 0, :713
        "positioned": rng.between(0, 1),        # status bit 1, :723
        "south": rng.between(0, 1),             # status bit 2, :728
        "west": rng.between(0, 1),              # status bit 3, :734
        "lat": rng.between(0, 90_000_000),      # millionths of a degree, :725
        "lon": rng.between(0, 180_000_000),     # :726
        "altitude": rng.between(-500, 6000),    # metres, signed, :760; range is rule R12
        "speed": rng.between(0, 2000),          # tenths of km/h, :761; range is rule R12
        "course": rng.between(0, 359),          # degrees, :762
        "time": time,                           # BCD YYMMDDhhmmss, :763 and :259-268
    }
    while True:
        chosen = _choose_items(rng, rng.between(*item_range))
        if sum(2 + ITEMS[i] for i in chosen) != forbidden_items_length:
            break
    for item in chosen:
        f[f"item_{item:02x}"] = rng.below(1 << (8 * ITEMS[item]))
    return f


def _choose_items(rng, k):
    """k distinct item IDs, in ascending order."""
    pool = sorted(ITEMS)
    for i in range(min(k, len(pool))):
        j = i + rng.below(len(pool) - i)
        pool[i], pool[j] = pool[j], pool[i]
    return sorted(pool[:min(k, len(pool))])


def location_body(f):
    status = f["acc"] | f["positioned"] << 1 | f["south"] << 2 | f["west"] << 3
    body = (f["alarm"].to_bytes(4, "big") + status.to_bytes(4, "big")
            + f["lat"].to_bytes(4, "big") + f["lon"].to_bytes(4, "big")
            + f["altitude"].to_bytes(2, "big", signed=True)
            + f["speed"].to_bytes(2, "big") + f["course"].to_bytes(2, "big") + bcd(f["time"]))
    for item in sorted(ITEMS):
        key = f"item_{item:02x}"
        if key in f:
            body += bytes([item, ITEMS[item]]) + f[key].to_bytes(ITEMS[item], "big")
    return body


# --- Location batch, 0x0704 -------------------------------------------------------------------

def batch_fields(rng, times, item_range):
    """decodeLocationBatch, :1634-1655: a count, a type (non-zero marks the batch as archived,
    :1648), then each record as a 2-byte length and a location body. One record per time given."""
    return {"archive": rng.between(0, 1),
            "records": [location_fields(rng, t, item_range, 20) for t in times]}


def batch_body(f):
    body = len(f["records"]).to_bytes(2, "big") + bytes([f["archive"]])
    for record in f["records"]:
        r = location_body(record)
        body += len(r).to_bytes(2, "big") + r
    return body


# --- Location report 2, 0x5501 ----------------------------------------------------------------

def location2_fields(rng, time):
    """Jt600ProtocolDecoder.decodeBinaryLocation, :95-116, then decodeLocation2, :1529-1548.
    Coordinates are BCD degrees and minutes, DDMM.mmmm and DDDMM.mmmm (:50-54). Rule R13: no
    trailing items."""
    return {
        "time": time,
        "lat": rng.between(0, 89) * 1_000_000 + rng.between(0, 59) * 10_000 + rng.between(0, 9999),
        "lon": rng.between(0, 179) * 1_000_000 + rng.between(0, 59) * 10_000 + rng.between(0, 9999),
        "valid": rng.between(0, 1),             # flags bit 0, :110
        "north": rng.between(0, 1),             # flags bit 1, :111
        "east": rng.between(0, 1),              # flags bit 2, :112
        "speed": rng.between(0, 99),            # two BCD digits, :114
        "course": rng.between(0, 179),          # degrees / 2, :115
        "rssi": rng.between(0, 31),             # :1529; ranges from here on are rule R12
        "satellites": rng.between(0, 12),       # :1530
        "odometer": rng.below(1 << 32),         # :1531
        "battery": rng.between(0, 100),         # percent, :1533-1535
        "cid": rng.below(1 << 32),              # :1540
        "lac": rng.below(1 << 16),              # :1541
        "product": rng.between(0, 3),           # :1546
        "status": rng.below(1 << 16),           # :1547
        "alarm": rng.below(1 << 16),            # :1548
    }


def location2_body(f):
    t, lon = f["time"], f"{f['lon']:09d}"
    flags = f["valid"] | f["north"] << 1 | f["east"] << 2
    return (bcd(t[4:6] + t[2:4] + t[0:2])  # day, month, year: :98-100
            + bcd(t[6:12])
            + bcd(f"{f['lat']:08d}")
            # 9 BCD digits: the 9th shares its byte with the flags. BcdUtil.readInteger peeks at
            # the high nibble without consuming it (helper/BcdUtil.java), then :109 reads the byte.
            + bcd(lon[:8]) + bytes([int(lon[8]) << 4 | flags])
            + bcd(f"{f['speed']:02d}") + bytes([f["course"], f["rssi"], f["satellites"]])
            + f["odometer"].to_bytes(4, "big") + bytes([f["battery"]])
            + f["cid"].to_bytes(4, "big") + f["lac"].to_bytes(2, "big") + bytes([f["product"]])
            + f["status"].to_bytes(2, "big") + f["alarm"].to_bytes(2, "big"))


# --- "(" … ")" sentence ---------------------------------------------------------------------

def sentence_fields(rng, terminal, index):
    """Rule R14. The shape is that of the two sentences in Traccar's tests
    (Jt808ProtocolDecoderTest.java:215 and :268): ID, 1, a 3-digit sequence, a command and its
    arguments. No bytes are copied from them. The decoder distinguishes only whether a sentence
    contains "BASE,2" (Jt808ProtocolDecoder.java:347), so half are that and half are not."""
    head = f"{terminal},1,{index % 1000:03d},"
    if rng.below(2):
        return {"text": head + "BASE,2,TIME"}
    return {"text": head + f"RESULT,{rng.between(1, 9)},{rng.digits(6)}"}


def sentence(f):
    return b"(" + f["text"].encode("ascii") + b")"
