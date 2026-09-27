"""The traffic model: connections, frames, faults, garbage, and chunks in an interleaved order.

Every number that shapes the traffic comes from the parameter file, and every one of them is an
assumption. bench/SPEC.md lists each as unset, with no source ("What this specification does not
fix"). So the file must state all of them: there are no defaults to fall back on.

The structural choices that are not numbers are RULES below. They are assumptions too. The
manifest carries them, so a result can say which rules produced its input.
"""

from dataclasses import dataclass, field

import common
import gt06
import jt808
from prng import PPM

FAULTS = ("truncated", "bad_checksum", "length_disagreement", "unknown_type", "flag_lying")
ALL_BYTES = bytes(range(256))

# Rule R16: the bytes each protocol's framer treats as a boundary. Gt06FrameDecoder.java:40 tests
# for 0x78 and assumes 0x79 otherwise, and :50-56 scans for 0D 0A. Jt808FrameDecoder.java:37 scans
# for "(", 7E and E7, and :51 for ")".
SYNC_BYTES = {"gt06": (0x78, 0x79, 0x0D, 0x0A), "jt808": (0x28, 0x29, 0x7E, 0xE7)}

RULES = {
    "R1": "A connection carries one protocol and one device for its whole life.",
    "R2": "A connection's first frame is its session frame: GT06 login, JT808 terminal "
          "authentication. Session frames are never faulty and never preceded by garbage.",
    "R3": "A JT808 connection keeps one delimiter (7E or E7) and one format (2013 or 2019). "
          "\"(\" sentences may appear on any JT808 connection.",
    "R4": "At most one fault per frame. A fault's rate is a probability per frame eligible for it. "
          "Truncated: any non-session frame. Bad checksum, length disagreement, unknown type: any "
          "non-session GT06 frame or JT808 binary frame. Flag-lying: JT808 binary frames on "
          "2013-format connections.",
    "R5": "A device clock starts at a uniformly random second of 2026 and advances 1-120 s per "
          "frame. A batch's records are 10 s apart and end at the frame's time.",
    "R6": "Field values are uniform over the ranges the sources give, cited in gt06.py and "
          "jt808.py. They set how often a JT808 byte needs escaping, which the manifest reports.",
    "R7": "GT06 serial numbers start at 1 (vendor document §4.5); JT808 message indices start at "
          "0. Both advance by one per frame.",
    "R8": "The version byte of a 2019-format JT808 header is 1.",
    "R9": "The alternative (E7) escape alphabet escapes 0x3D as 3E 02, the inverse of the decode "
          "table.",
    "R10": "JT808 authentication uses the 2013 body, a code of 0-9 and A-Z, in both formats.",
    "R11": "No location report's items are 20 bytes as Traccar counts them "
           "(Jt808ProtocolDecoder.java:765), which it would read as a vendor format.",
    "R12": "Ranges no source gives: a JT808 alarm word is 0 with probability 3/4, else one random "
           "bit; altitude -500 to 6000 m; speed 0 to 200 km/h; 0x5501 RSSI 0-31, satellites "
           "0-12, battery 0-100, product 0-3.",
    "R13": "A 0x5501 report carries no trailing items.",
    "R14": "A \"(\" sentence is ID,1,sequence,command: half BASE,2,TIME and half "
           "RESULT,<digit>,<6 digits>.",
    "R15": "Truncation keeps a uniformly random prefix of at least one byte and drops at least one. "
           "A bad checksum XORs a random non-zero value into the correct one. A length "
           "disagreement moves the length field by 1 to 4, either way, and the check is "
           "recomputed. An unknown-type frame is otherwise valid, with 0-32 random body bytes.",
    "R16": "Garbage appears only between two frames of one connection. \"no_sync\" garbage "
           "excludes the bytes the protocol's framer treats as boundaries: GT06 78 79 0D 0A, "
           "JT808 28 29 7E E7.",
    "R17": "Chunks are cut from each connection's byte stream without regard to frame boundaries "
           "(SPEC §3). A connection's chunks keep their order.",
}

# The parameter file's exact shape. "range" is [lo, hi], inclusive; a tuple lists allowed words.
SCHEMA = {
    "purpose": str,
    "connections": int,
    "frames": int,
    "assignment": ("equal", "uniform"),
    "protocol_weights": {"gt06": int, "jt808": int},
    "gt06": {"type_weights": {"location": int, "status": int}},
    "jt808": {
        "delimiter_weights": {"7e": int, "e7": int},
        "version_weights": {"2013": int, "2019": int},
        "type_weights": {"location": int, "batch": int, "location2": int, "sentence": int},
        "batch_records": "range",
        "location_items": "range",
        "auth_code_length": "range",
    },
    "faults_ppm": {name: int for name in FAULTS},
    "garbage": {"rate_ppm": int, "length": "range", "alphabet": ("any", "no_sync")},
    "chunk_size": "range",
    "interleave": ("sequential", "round_robin", "uniform"),
}


class ParamError(ValueError):
    pass


def validate(params):
    """Check a parameter file against SCHEMA, then the limits the formats impose."""
    _check(params, SCHEMA, "")

    def need(ok, message):
        if not ok:
            raise ParamError(message)

    p, j = params, params["jt808"]
    need(1 <= p["connections"] <= 0x10000, "connections: 1 to 65536 (the container's u16)")
    need(p["frames"] >= p["connections"], "frames: at least one per connection, its session frame")
    need(sum(p["faults_ppm"].values()) <= PPM, "faults_ppm: the rates must sum to at most 1000000")
    need(p["garbage"]["rate_ppm"] <= PPM, "garbage.rate_ppm: at most 1000000")
    need(p["garbage"]["length"][0] >= 1, "garbage.length: a run is at least 1 byte")
    need(p["chunk_size"][0] >= 1 and p["chunk_size"][1] <= 0xFFFF, "chunk_size: 1 to 65535")
    need(j["batch_records"][0] >= 1, "jt808.batch_records: at least 1")
    need(j["auth_code_length"][0] >= 1, "jt808.auth_code_length: at least 1")
    need(j["location_items"][1] <= len(jt808.ITEMS), f"jt808.location_items: at most {len(jt808.ITEMS)}")
    # A JT808 body length has 10 bits (Jt808ProtocolDecoder.java:363), so no body may pass 1023.
    items = sum(sorted((2 + n for n in jt808.ITEMS.values()), reverse=True)[:j["location_items"][1]])
    batch = 3 + j["batch_records"][1] * (2 + 28 + items)
    need(batch <= 0x3FF, f"jt808.batch_records: {j['batch_records'][1]} records with up to "
                         f"{j['location_items'][1]} items each can make a {batch}-byte body, and a "
                         "JT808 body length has 10 bits, so at most 1023")
    need(j["auth_code_length"][1] <= 0x3FF, "jt808.auth_code_length: at most 1023, the body limit")
    for path, table in (("protocol_weights", p["protocol_weights"]),
                        ("gt06.type_weights", p["gt06"]["type_weights"]),
                        ("jt808.delimiter_weights", j["delimiter_weights"]),
                        ("jt808.version_weights", j["version_weights"]),
                        ("jt808.type_weights", j["type_weights"])):
        need(sum(table.values()) > 0, f"{path}: at least one weight must be positive")


def _check(value, schema, path):
    where = path or "the parameter file"
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise ParamError(f"{where}: expected an object")
        missing = [k for k in schema if k not in value]
        if missing:
            raise ParamError(f"{where}: missing {', '.join(missing)}. Every parameter must be "
                             "stated; none has a default (bench/SPEC.md: no source exists).")
        extra = [k for k in value if k not in schema]
        if extra:
            raise ParamError(f"{where}: unknown {', '.join(extra)}")
        for k, sub in schema.items():
            _check(value[k], sub, f"{path}.{k}" if path else k)
    elif schema == "range":
        if not (isinstance(value, list) and len(value) == 2 and all(_is_int(v) for v in value)
                and 0 <= value[0] <= value[1]):
            raise ParamError(f"{where}: expected [lo, hi] with 0 <= lo <= hi")
    elif isinstance(schema, tuple):
        if value not in schema:
            raise ParamError(f"{where}: expected one of {', '.join(schema)}")
    elif schema is int:
        if not (_is_int(value) and value >= 0):
            raise ParamError(f"{where}: expected a non-negative integer")
    elif not isinstance(value, schema):
        raise ParamError(f"{where}: expected {schema.__name__}")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


@dataclass
class Segment:
    kind: str       # "frame" or "garbage"
    data: bytes
    record: dict    # what the generator intended; generate.py adds offsets for the intent log


@dataclass
class Connection:
    conn: int
    protocol: str
    device: str
    delimiter: int = None   # JT808 only
    version: int = None     # JT808 only: 2013 or 2019
    clock: int = 0
    counter: int = 0
    segments: list = field(default_factory=list)

    def stream(self):
        return b"".join(s.data for s in self.segments)

    def record(self):
        r = {"kind": "connection", "conn": self.conn, "protocol": self.protocol, "device": self.device}
        if self.protocol == "jt808":
            r.update(delimiter=f"{self.delimiter:02x}", version=self.version)
        return r


def generate(params, rng):
    """The connections, each with its segments, and the interleaved chunks: [(conn, bytes)]."""
    validate(params)
    conns = [_connection(rng, params, c) for c in range(params["connections"])]
    for conn, n in zip(conns, _frames_per_connection(rng, params)):
        _fill(rng, params, conn, n)
    per_conn = [_chunks(rng, params, conn.stream()) for conn in conns]
    return conns, _interleave(rng, params, per_conn)


def _connection(rng, p, c):
    protocol = rng.pick(p["protocol_weights"])
    if protocol == "gt06":
        conn = Connection(c, protocol, common.fake_imei(rng), counter=1)  # R7
    else:
        j = p["jt808"]
        delimiter = {"7e": jt808.STANDARD, "e7": jt808.ALTERNATIVE}[rng.pick(j["delimiter_weights"])]
        conn = Connection(c, protocol, common.fake_terminal(rng), delimiter,
                          int(rng.pick(j["version_weights"])))
    conn.clock = rng.below(common.YEAR_SECONDS)  # R5
    return conn


def _frames_per_connection(rng, p):
    """Every connection gets its session frame; the rest are dealt equally or uniformly at random."""
    c, extra = p["connections"], p["frames"] - p["connections"]
    if p["assignment"] == "equal":
        return [1 + extra // c + (1 if i < extra % c else 0) for i in range(c)]
    counts = [1] * c
    for _ in range(extra):
        counts[rng.below(c)] += 1
    return counts


def _fill(rng, p, conn, n):
    for k in range(n):
        if k > 0 and rng.chance(p["garbage"]["rate_ppm"]):  # R16: between frames only
            conn.segments.append(_garbage(rng, p, conn))
        make = _gt06_frame if conn.protocol == "gt06" else _jt808_frame
        conn.segments.append(make(rng, p, conn, session=(k == 0)))
        conn.clock += rng.between(1, 120)  # R5
        conn.counter += 1


def _fault(rng, p, eligible):
    """One draw, whatever is eligible, so the eligibility of one frame never shifts another's."""
    u = rng.below(PPM)
    for name in FAULTS:
        if name in eligible:
            if u < p["faults_ppm"][name]:
                return name
            u -= p["faults_ppm"][name]
    return None


def _length_delta(rng, correct, limit):
    """R15: a non-zero change of 1 to 4 either way, kept inside [0, limit]."""
    d = rng.between(1, 4) * (1 if rng.below(2) else -1)
    return d if 0 <= correct + d <= limit else -d


def _truncate(rng, data, record):
    record["frame_length"] = len(data)
    return data[:rng.between(1, len(data) - 1)]  # R15


def _frame_record(conn, framing, msg_type, fault, fields):
    return {"kind": "frame", "conn": conn.conn, "protocol": conn.protocol, "framing": framing,
            "type": msg_type, "fault": fault, "fields": fields}


def _gt06_frame(rng, p, conn, session):
    serial = conn.counter & 0xFFFF
    if session:
        f = gt06.login_fields(conn.device)
        rec = _frame_record(conn, "7878", "0x01", None, f)
        rec["serial"] = serial
        return Segment("frame", gt06.frame(gt06.LOGIN, gt06.login_content(f), serial), rec)

    fault = _fault(rng, p, ("truncated", "bad_checksum", "length_disagreement", "unknown_type"))
    if fault == "unknown_type":
        number = gt06.UNKNOWN[rng.below(len(gt06.UNKNOWN))]
        content = rng.bytes_from(rng.between(0, 32), ALL_BYTES)
        f = {"content": content.hex()}
    else:
        name = rng.pick(p["gt06"]["type_weights"])
        number, encode = gt06.TYPES[name]
        f = (gt06.location_fields(rng, common.clock_digits(conn.clock)) if name == "location"
             else gt06.status_fields(rng))
        content = encode(f)
    rec = _frame_record(conn, "7878", f"0x{number:02x}", fault, f)
    rec["serial"] = serial

    length, crc_error = None, 0
    if fault == "length_disagreement":
        length = 5 + len(content) + _length_delta(rng, 5 + len(content), 0xFF)
        rec["length_field"] = length
    elif fault == "bad_checksum":
        crc_error = rng.between(1, 0xFFFF)
        rec["check_error"] = crc_error
    data = gt06.frame(number, content, serial, length, crc_error)
    if fault == "truncated":
        data = _truncate(rng, data, rec)
    return Segment("frame", data, rec)


def _jt808_frame(rng, p, conn, session):
    j = p["jt808"]
    framing = f"{conn.delimiter:02x}"
    header = dict(delimiter=conn.delimiter, terminal=conn.device, index=conn.counter,
                  version_2019=(conn.version == 2019))
    if session:
        f = jt808.auth_fields(rng, j["auth_code_length"])
        rec = _frame_record(conn, framing, "0x0102", None, f)
        rec["index"] = conn.counter & 0xFFFF
        data = jt808.frame(jt808.AUTH, jt808.auth_body(f), **header)
        rec["escapes"] = _escapes(data)
        return Segment("frame", data, rec)

    name = rng.pick(j["type_weights"])
    if name == "sentence":
        fault = _fault(rng, p, ("truncated",))
        f = jt808.sentence_fields(rng, conn.device, conn.counter)
        rec = _frame_record(conn, "paren", "sentence", fault, f)
        data = jt808.sentence(f)
        return Segment("frame", _truncate(rng, data, rec) if fault else data, rec)

    eligible = ("truncated", "bad_checksum", "length_disagreement", "unknown_type")
    if conn.version == 2013:
        eligible += ("flag_lying",)
    fault = _fault(rng, p, eligible)
    now = common.clock_digits(conn.clock)
    if fault == "unknown_type":
        msg_type = jt808.UNKNOWN[rng.below(len(jt808.UNKNOWN))]
        body = rng.bytes_from(rng.between(0, 32), ALL_BYTES)
        f = {"body": body.hex()}
    elif name == "location":
        msg_type = jt808.LOCATION
        f = jt808.location_fields(rng, now, j["location_items"], 18)
        body = jt808.location_body(f)
    elif name == "batch":
        msg_type = jt808.BATCH
        n = rng.between(*j["batch_records"])
        times = [common.clock_digits(conn.clock - 10 * (n - 1 - i)) for i in range(n)]  # R5
        f = jt808.batch_fields(rng, times, j["location_items"])
        body = jt808.batch_body(f)
    else:
        msg_type = jt808.LOCATION2
        f = jt808.location2_fields(rng, now)
        body = jt808.location2_body(f)

    rec = _frame_record(conn, framing, f"0x{msg_type:04x}", fault, f)
    rec["index"] = conn.counter & (0xFF if msg_type in jt808.SHORT_INDEX else 0xFFFF)
    extra = {}
    if fault == "length_disagreement":
        extra["body_length"] = len(body) + _length_delta(rng, len(body), 0x3FF)
        rec["length_field"] = extra["body_length"]
    elif fault == "bad_checksum":
        extra["check_error"] = rng.between(1, 0xFF)
        rec["check_error"] = extra["check_error"]
    elif fault == "flag_lying":
        extra["flag_lie"] = True
    data = jt808.frame(msg_type, body, **header, **extra)
    rec["escapes"] = _escapes(data)
    if fault == "truncated":
        data = _truncate(rng, data, rec)
    return Segment("frame", data, rec)


def _escapes(frame):
    """Escape pairs in a whole frame: the bytes between its delimiters that introduce one."""
    table = jt808.ESCAPE[frame[0]]
    introducers = {v[0] for v in table.values()}
    inner, count, i = frame[1:-1], 0, 0
    while i < len(inner):
        if inner[i] in introducers:
            count, i = count + 1, i + 2
        else:
            i += 1
    return count


def _garbage(rng, p, conn):
    g = p["garbage"]
    alphabet = ALL_BYTES if g["alphabet"] == "any" else bytes(
        b for b in range(256) if b not in SYNC_BYTES[conn.protocol])
    data = rng.bytes_from(rng.between(*g["length"]), alphabet)
    return Segment("garbage", data, {"kind": "garbage", "conn": conn.conn, "alphabet": g["alphabet"]})


def _chunks(rng, p, stream):
    """R17: cut with no regard to frame boundaries."""
    out, i = [], 0
    while i < len(stream):
        n = rng.between(*p["chunk_size"])
        out.append(stream[i:i + n])
        i += n
    return out


def _interleave(rng, p, per_conn):
    """[(conn, chunk)] in delivery order. sequential: each connection's chunks together, which SPEC
    §7 warns measures a locality line-rate traffic lacks. round_robin: one chunk from each connection
    in turn. uniform: each chunk from a uniformly chosen connection that still has chunks."""
    order, pos = [], [0] * len(per_conn)
    active = [c for c, chunks in enumerate(per_conn) if chunks]
    mode = p["interleave"]
    while active:
        k = rng.below(len(active)) if mode == "uniform" else 0
        c = active[k]
        order.append((c, per_conn[c][pos[c]]))
        pos[c] += 1
        if mode == "round_robin":
            active.append(active.pop(k))  # to the back of the queue
        if pos[c] == len(per_conn[c]):
            active.remove(c)
    return order
