"""GT06 frames, laid out from the vendor document and Traccar. Citation keys: see common.py.

    78 78 | length | protocol | content | serial | CRC | 0D 0A        [doc] §4, p.9
    length = protocol + content + serial + CRC = 5 + N               [doc] §4.2, p.9
    CRC-ITU over length .. serial                                    [doc] §4.6, p.10

The three frame types of bench/SPEC.md §2, each in its STANDARD layout: a length that no rule in
[traccar] Gt06ProtocolDecoder.java:1642-1703 assigns to another variant (PROTOCOL-EVIDENCE
Finding 7). Byte-exact anchors, in test_stimulus.py: the document's login example (p.12), and its
location example (p.16) with the byte its own table corrects (Finding 5).
"""

from common import bcd

START = b"\x78\x78"
STOP = b"\x0d\x0a"

LOGIN, LOCATION, STATUS = 0x01, 0x12, 0x13  # [doc] §4.3, p.9

# Protocol numbers for SPEC §4's unknown message type. None appears anywhere in
# [traccar] Gt06ProtocolDecoder.java as a MSG_ constant, a case label or an == operand, so no
# decoder in the reference family gives it a meaning. test_stimulus.py re-derives this from the
# source when reference/ is present.
UNKNOWN = (0x08, 0x3A, 0x3C, 0x3D, 0x3E, 0x3F, 0x42, 0x43)


def _crc_table():
    """The reflected CRC-ITU table (polynomial 0x8408), computed from the bit-serial definition."""
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
        table.append(crc)
    return table


_TABLE = _crc_table()


def crc_itu(data):
    """CRC-ITU as the vendor's GetCrc16 computes it ([doc] Appendix A, p.37): start at 0xFFFF,
    one table step per byte, invert. check.py verifies frames through a different CRC path."""
    fcs = 0xFFFF
    for b in data:
        fcs = (fcs >> 8) ^ _TABLE[(fcs ^ b) & 0xFF]
    return ~fcs & 0xFFFF


def frame(protocol, content, serial, length=None, crc_error=0):
    """One 0x7878 frame.

    `length` replaces the correct length field (SPEC §4, length-field disagreement). The CRC then
    covers the length actually written, so the length is the frame's only fault. `crc_error` is
    XORed into the correct CRC (SPEC §4, bad checksum)."""
    n = 5 + len(content) if length is None else length
    if not 0 <= n <= 0xFF:
        raise ValueError(f"length {n} does not fit the 0x7878 length byte")
    covered = bytes([n, protocol]) + content + serial.to_bytes(2, "big")
    return START + covered + (crc_itu(covered) ^ crc_error).to_bytes(2, "big") + STOP


# --- Login, 0x01 -------------------------------------------------------------------------------

def login_fields(imei):
    return {"imei": imei}


def login_content(f):
    """The IMEI's 15 digits as BCD after a leading 0 ([doc] §5.1.1.4, p.11). [traccar]
    Gt06ProtocolDecoder.java:523 reads it back as hexDump(8).substring(1)."""
    return bcd("0" + f["imei"])


# --- Location, 0x12 ----------------------------------------------------------------------------

def location_fields(rng, time):
    """Each field uniform over the range the document gives for it ([doc] §5.2.1, p.13-16)."""
    return {
        "time": time,                              # YYMMDDhhmmss                  §5.2.1.4
        "satellites": rng.between(0, 15),          # a nibble                      §5.2.1.5
        "lat": rng.between(0, 162_000_000),        # minutes × 30000, 0°-90°       §5.2.1.6
        "lon": rng.between(0, 324_000_000),        # minutes × 30000, 0°-180°      §5.2.1.7
        "speed": rng.between(0, 255),              # km/h                          §5.2.1.8
        "course": rng.between(0, 360),             # degrees                       §5.2.1.9
        "differential": rng.between(0, 1),
        "positioned": rng.between(0, 1),
        "west": rng.between(0, 1),
        "north": rng.between(0, 1),
        "mcc": rng.between(0, 0x3E7),              #                               §5.2.1.10
        "mnc": rng.between(0, 0xFF),               # one byte                      §5.2.1.11
        "lac": rng.between(0x0001, 0xFFFE),        # 0x0000 and 0xFFFF excluded    §5.2.1.12
        "cell": rng.between(0, 0xFFFFFF),          #                               §5.2.1.13
    }


def location_content(f):
    """[doc] §5.2.1, p.13; read back by [traccar] Gt06ProtocolDecoder.java:915 decodeGps (:301-351)
    and :927 decodeLbs (:353-410), with no LBS length byte and a 1-byte MNC (MCC bit 15 clear)."""
    t = f["time"]
    course_status = (f["differential"] << 13 | f["positioned"] << 12 | f["west"] << 11
                     | f["north"] << 10 | f["course"])  # [doc] §5.2.1.9, p.15; [traccar] :333-341
    return (bytes(int(t[i:i + 2]) for i in range(0, 12, 2))  # binary, not BCD: 2010 is 0x0A
            + bytes([0xC0 | f["satellites"]])  # high nibble: the GPS block is 12 bytes, §5.2.1.5
            + f["lat"].to_bytes(4, "big") + f["lon"].to_bytes(4, "big")
            + bytes([f["speed"]]) + course_status.to_bytes(2, "big")
            + f["mcc"].to_bytes(2, "big") + bytes([f["mnc"]])
            + f["lac"].to_bytes(2, "big") + f["cell"].to_bytes(3, "big"))


# --- Status (heartbeat), 0x13 ------------------------------------------------------------------

def status_fields(rng):
    """[doc] §5.4.1, p.24-25. Terminal information: bit 7 oil and electricity disconnected, bit 6
    GPS tracking on, bits 5-3 an alarm code 0-4, bit 2 charging, bit 1 ACC high, bit 0 activated."""
    info = rng.below(0x100) & 0b11000111 | rng.between(0, 4) << 3
    return {
        "info": info,
        "voltage": rng.between(0, 6),              # §5.4.1.5
        "gsm": rng.between(0, 4),                  # §5.4.1.6
        "alarm": rng.between(0, 5),                # §5.4.1.7, former byte
        "language": rng.between(1, 2),             # §5.4.1.7, latter byte
    }


def status_content(f):
    """Five bytes, as the field table gives them ([doc] p.24), not the 3-byte form the p.26
    example's length and CRC were computed for (PROTOCOL-EVIDENCE Finding 5). Length 0x0A, which
    [traccar] :1670 does not claim for OBD6, so the decoder takes the path at :896-998."""
    return bytes([f["info"], f["voltage"], f["gsm"], f["alarm"], f["language"]])


TYPES = {
    "location": (LOCATION, location_content),
    "status": (STATUS, status_content),
}
