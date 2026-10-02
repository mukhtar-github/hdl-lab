#!/usr/bin/env python3
"""Tests for bench/stimulus.  make -C bench/stimulus test

  Anchors      the encoders reproduce published bytes: the GT06 vendor document's examples,
               Traccar's escaping test, and 50 outputs of the SplitMix64 reference implementation.
  Layouts      what the sources fix about header and body lengths.
  Parameters   nothing has a default, and nothing a format cannot carry is accepted.
  Container    stimulus.bin's layout, byte for byte as decisions/0014 states it, and what it refuses.
  Streams      what every stimulus must satisfy, and a checker that can be seen to fail.
"""

import contextlib
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(os.path.dirname(HERE)), "reference")
COVERAGE = os.path.join(HERE, "params", "coverage.json")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rv32"))

import check  # noqa: E402
import common  # noqa: E402
import container  # noqa: E402
import generate  # noqa: E402
import gt06  # noqa: E402
import jt808  # noqa: E402
import traffic  # noqa: E402
from crc_oracle import crc16_x25  # noqa: E402
from prng import SplitMix64  # noqa: E402

# rust-random/rngs at 84683fcacf9a5e346a945d1f620c772f91b4b82d, rand_xoshiro/src/splitmix64.rs:95-150:
# "These values were produced with the reference implementation" (Vigna's splitmix64.c). There,
# seed_from_u64 sets the state to the seed itself, as SplitMix64(seed) does here.
SPLITMIX64_SEED = 1477776061723855037
SPLITMIX64_REFERENCE = [
    1985237415132408290, 2979275885539914483, 13511426838097143398,
    8488337342461049707, 15141737807933549159, 17093170987380407015,
    16389528042912955399, 13177319091862933652, 10841969400225389492,
    17094824097954834098, 3336622647361835228, 9678412372263018368,
    11111587619974030187, 7882215801036322410, 5709234165213761869,
    7799681907651786826, 4616320717312661886, 4251077652075509767,
    7836757050122171900, 5054003328188417616, 12919285918354108358,
    16477564761813870717, 5124667218451240549, 18099554314556827626,
    7603784838804469118, 6358551455431362471, 3037176434532249502,
    3217550417701719149, 9958699920490216947, 5965803675992506258,
    12000828378049868312, 12720568162811471118, 245696019213873792,
    8351371993958923852, 14378754021282935786, 5655432093647472106,
    5508031680350692005, 8515198786865082103, 6287793597487164412,
    14963046237722101617, 3630795823534910476, 8422285279403485710,
    10554287778700714153, 10871906555720704584, 8659066966120258468,
    9420238805069527062, 10338115333623340156, 13514802760105037173,
    14635952304031724449, 15419692541594102413,
]

def coverage_params():
    with open(COVERAGE) as f:
        return json.load(f)


def run_generator(params, seed, out):
    path = os.path.join(out, "params.json")
    os.makedirs(out, exist_ok=True)
    with open(path, "w") as f:
        json.dump(params, f)
    with contextlib.redirect_stdout(io.StringIO()):
        status = generate.main(["--params", path, "--seed", str(seed), "--out", out])
    if status:
        raise AssertionError(f"generate.py exited {status}")


def run_check(out):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            status = check.check(out)
        except check.Mismatch as e:
            print(e)
            status = 1
    return status, buf.getvalue()


class Anchors(unittest.TestCase):

    def test_splitmix64_reference(self):
        rng = SplitMix64(SPLITMIX64_SEED)
        self.assertEqual([rng.next64() for _ in range(50)], SPLITMIX64_REFERENCE)

    def test_gt06_login_example(self):
        # GT06 v1.8.1 §5.1.3, PDF p.12 (the byte row; the hex string has a typo, reference/README).
        got = gt06.frame(gt06.LOGIN, gt06.login_content({"imei": "123456789012345"}), serial=1)
        self.assertEqual(got.hex(), "78780d01012345678901234500018cdd0d0a")

    def test_gt06_location_example_as_its_table_corrects_it(self):
        # §5.2.2, p.16, with byte 10 as the field table on p.13 gives it, 0xCF, not the string's 0xCC.
        # PROTOCOL-EVIDENCE Finding 5: that is the one single-byte change that makes its CRC verify.
        f = {"time": "110829174616", "satellites": 15, "lat": 0x027AC7EB, "lon": 0x0C465849,
             "speed": 0, "course": 0x08F, "differential": 0, "positioned": 1, "west": 0,
             "north": 1, "mcc": 0x01CC, "mnc": 0, "lac": 0x287D, "cell": 0x001FB8}
        got = gt06.frame(gt06.LOCATION, gt06.location_content(f), serial=3)
        self.assertEqual(got.hex(), "78781f120b081d112e10cf027ac7eb0c46584900148f01cc00287d"
                                    "001fb8000380810d0a")

    def test_gt06_server_replies(self):
        # §5.1.2, p.12 and §5.4.3, p.26: a reply is a frame with no content.
        self.assertEqual(gt06.frame(0x01, b"", serial=1).hex(), "787805010001d9dc0d0a")
        self.assertEqual(gt06.frame(0x13, b"", serial=0x11).hex(), "787805130011f9700d0a")

    def test_gt06_heartbeat_example_without_its_alarm_language_bytes(self):
        # §5.4.3, p.26. Its length and CRC fit only a 3-byte content (Finding 5).
        got = gt06.frame(0x13, bytes([0x4B, 0x04, 0x03]), serial=0x11)
        self.assertEqual(got.hex(), "787808134b04030011061f0d0a")

    def test_two_crc_paths_agree(self):
        self.assertEqual(gt06.crc_itu(b"123456789"), 0x906E)  # RevEng catalogue, CRC-16/X-25
        rng = SplitMix64(7)
        for n in range(64):
            data = rng.bytes_from(n, bytes(range(256)))
            self.assertEqual(gt06.crc_itu(data), crc16_x25(data))

    def test_jt808_escaping_traccar_vector(self):
        # Traccar 847edd2c, Jt808FrameDecoderTest.java:17-19: 7e 30 7d 02 08 7d 01 55 7e decodes to
        # 7e 30 7e 08 7d 55 7e. Escaping the inside must give the wire form back.
        self.assertEqual(jt808.escape(bytes.fromhex("307e087d55"), jt808.STANDARD).hex(),
                         "307d02087d0155")

    def test_jt808_escaping_round_trips_through_the_decoders_loop(self):
        for delimiter in (jt808.STANDARD, jt808.ALTERNATIVE):
            data = bytes(range(256))
            wire = jt808.escape(data, delimiter)
            self.assertNotIn(delimiter, wire)
            self.assertEqual(check.destuff(wire, delimiter), data)

    def test_luhn_matches_traccar(self):
        def traccar_luhn(imei):  # helper/Checksum.java:214-232, transcribed
            checksum, remain, i = 0, imei, 0
            while remain != 0:
                digit = remain % 10
                if i % 2 == 0:
                    digit *= 2
                    if digit >= 10:
                        digit = 1 + digit % 10
                checksum += digit
                remain //= 10
                i += 1
            return (10 - checksum % 10) % 10
        rng = SplitMix64(11)
        for _ in range(2000):
            digits = rng.digits(14)
            self.assertEqual(common.luhn_digit(digits), traccar_luhn(int(digits)))
            imei = common.fake_imei(rng)
            self.assertNotEqual(int(imei[14]), traccar_luhn(int(imei[:14])))

    @unittest.skipUnless(os.path.exists(os.path.join(REF, "Gt06ProtocolDecoder.java")),
                         "reference/ not fetched: see reference/README.md")
    def test_unknown_codes_are_unknown_to_traccar(self):
        def mentioned(name):
            with open(os.path.join(REF, name)) as f:
                src = f.read()
            pats = (r"MSG_\w+\s*=\s*0[xX]([0-9a-fA-F]+)", r"case\s+0[xX]([0-9a-fA-F]+)",
                    r"==\s*0[xX]([0-9a-fA-F]+)")
            return {int(v, 16) for p in pats for v in re.findall(p, src)}
        self.assertFalse(set(gt06.UNKNOWN) & mentioned("Gt06ProtocolDecoder.java"))
        self.assertFalse(set(jt808.UNKNOWN) & mentioned("Jt808ProtocolDecoder.java"))


class Layouts(unittest.TestCase):

    def test_jt808_header_is_5_plus_version_plus_id_plus_index(self):
        # bench/PROTOCOL-EVIDENCE.md Finding 2: 5 + {0,1} + {6,7,10} + {1,2}.
        for delimiter in (jt808.STANDARD, jt808.ALTERNATIVE):
            for v2019 in (False, True):
                for msg_type in (jt808.LOCATION, jt808.LOCATION2):
                    wire = jt808.frame(msg_type, b"", delimiter=delimiter, terminal="000001234567",
                                       index=0, version_2019=v2019)
                    header = len(check.destuff(wire[1:-1], delimiter)) - 1  # less the check
                    want = 4 + v2019 + (10 if v2019 else 7 if delimiter == 0xE7 else 6) + (
                        1 if msg_type == jt808.LOCATION2 else 2)
                    self.assertEqual(header, want, (delimiter, v2019, msg_type))

    def test_gt06_lengths_are_standard(self):
        # PROTOCOL-EVIDENCE Finding 7: 0x12 at 0x21, 0x24, 0x29, 0x2B or >= 0x71, and 0x13 at 0x13,
        # would each select another variant.
        rng = SplitMix64(3)
        loc = gt06.frame(gt06.LOCATION, gt06.location_content(gt06.location_fields(rng, "260101000000")), 1)
        sts = gt06.frame(gt06.STATUS, gt06.status_content(gt06.status_fields(rng)), 1)
        self.assertEqual((loc[2], sts[2]), (0x1F, 0x0A))

    def test_location_items_never_take_traccars_vendor_path(self):
        # Rule R11: Jt808ProtocolDecoder.java:765 reads a 20-byte remainder as a vendor format. In a
        # frame the remainder includes the check and the closing delimiter, in a batch record not.
        p = coverage_params()
        p["protocol_weights"] = {"gt06": 0, "jt808": 1}
        p["jt808"].update(location_items=[0, 6], batch_records=[1, 17])
        conns, _ = traffic.generate(p, SplitMix64(5))

        def items_length(f):
            return sum(2 + jt808.ITEMS[int(k[5:], 16)] for k in f if k.startswith("item_"))
        seen = 0
        for conn in conns:
            for seg in conn.segments:
                r = seg.record
                if r.get("type") == "0x0200" and r["fault"] != "unknown_type":
                    self.assertNotEqual(items_length(r["fields"]), 18)
                    seen += 1
                if r.get("type") == "0x0704" and r["fault"] != "unknown_type":
                    for rec in r["fields"]["records"]:
                        self.assertNotEqual(items_length(rec), 20)
        self.assertGreater(seen, 50)


class Parameters(unittest.TestCase):

    def test_coverage_file_is_valid(self):
        traffic.validate(coverage_params())

    def test_every_parameter_is_required(self):
        def leaves(schema, path=()):
            for k, sub in schema.items():
                yield path + (k,)
                if isinstance(sub, dict):
                    yield from leaves(sub, path + (k,))
        for path in leaves(traffic.SCHEMA):
            p = coverage_params()
            node = p
            for k in path[:-1]:
                node = node[k]
            del node[path[-1]]
            with self.assertRaises(traffic.ParamError) as e:
                traffic.validate(p)
            self.assertIn(path[-1], str(e.exception))

    def test_unknown_parameter_is_rejected(self):
        p = coverage_params()
        p["garbage"]["rate"] = 1
        with self.assertRaisesRegex(traffic.ParamError, "unknown rate"):
            traffic.validate(p)

    def test_a_batch_the_length_field_cannot_state_is_rejected(self):
        p = coverage_params()
        p["jt808"].update(location_items=[6, 6], batch_records=[18, 18])  # 3 + 18 * 58 = 1047
        with self.assertRaisesRegex(traffic.ParamError, "1047-byte body"):
            traffic.validate(p)


class Container(unittest.TestCase):

    # decisions/0014, section 2, written out by hand for two connections and two chunks:
    #   header  "TFDS", version 2, 20 header bytes, 2 chunks, 2 connections, 4 payload bytes
    #   table   GT06, JT808, two bytes of padding
    #   chunks  3 bytes for connection 0 and one byte of padding; 1 byte for connection 1 and three
    EXAMPLE_CHUNKS = [(0, bytes.fromhex("78780d")), (1, bytes.fromhex("7e"))]
    EXAMPLE = bytes.fromhex("54464453 0200 1400 02000000 02000000 04000000"
                            "01 02 0000"
                            "0300 0000 78780d 00"
                            "0100 0100 7e 000000")

    def test_the_layout_is_the_one_0014_states(self):
        self.assertEqual(container.pack(self.EXAMPLE_CHUNKS, ["gt06", "jt808"]), self.EXAMPLE)
        self.assertEqual(container.unpack(self.EXAMPLE), (["gt06", "jt808"], self.EXAMPLE_CHUNKS))

    def test_what_unpack_refuses(self):
        def edit(offset, value):
            blob = bytearray(self.EXAMPLE)
            blob[offset] = value
            return bytes(blob)
        refused = {
            "version 1": edit(4, 1),
            "protocol code 0": edit(20, 0),
            "protocol code 3": edit(21, 3),
            "non-zero padding after the table": edit(22, 1),
            "a table that runs past the end": self.EXAMPLE[:12] + (99).to_bytes(4, "little")
                                              + self.EXAMPLE[16:],
        }
        for name, blob in refused.items():
            with self.subTest(name), self.assertRaises(ValueError):
                container.unpack(blob)

    def test_pack_refuses_an_unknown_protocol(self):
        with self.assertRaises(ValueError):
            container.pack(self.EXAMPLE_CHUNKS, ["gt06", "jt809"])


class Streams(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="stimulus-test-")
        cls.out = os.path.join(cls.tmp, "coverage-1")
        run_generator(coverage_params(), 1, cls.out)
        with open(os.path.join(cls.out, "manifest.json")) as f:
            cls.manifest = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def outputs(self, out):
        with open(os.path.join(out, "manifest.json")) as f:
            return json.load(f)["outputs"]

    def test_same_seed_same_stimulus_other_seed_other_stimulus(self):
        again = os.path.join(self.tmp, "again")
        other = os.path.join(self.tmp, "other")
        run_generator(coverage_params(), 1, again)
        run_generator(coverage_params(), 2, other)
        self.assertEqual(self.outputs(again), self.outputs(self.out))
        self.assertNotEqual(self.outputs(other)["stimulus.bin"], self.outputs(self.out)["stimulus.bin"])

    def test_coverage_run_contains_every_class(self):
        r = self.manifest["realized"]
        types = set(r["frames_by_type"])
        for t in ("gt06 0x01", "gt06 0x12", "gt06 0x13", "jt808 0x0102", "jt808 0x0200",
                  "jt808 0x0704", "jt808 0x5501", "jt808 sentence"):
            self.assertIn(t, types)
        self.assertTrue(any(t.startswith("gt06 ") and int(t[5:], 16) in gt06.UNKNOWN for t in types))
        self.assertTrue(any(t.startswith("jt808 0x0f") for t in types))
        self.assertEqual(set(r["frames_by_framing"]), {"7878", "7e", "e7", "paren"})
        self.assertEqual(set(r["frames_by_fault"]), set(traffic.FAULTS) | {"none"})
        c = r["counts"]
        for k in ("connections.jt808.version_2013", "connections.jt808.version_2019",
                  "connections.jt808.delimiter_7e", "connections.jt808.delimiter_e7",
                  "garbage.runs", "jt808.escape_pairs"):
            self.assertGreater(c.get(k, 0), 0, k)
        self.assertGreater(r["frames_split_across_chunks"], 0)

    def test_check_passes(self):
        status, text = run_check(self.out)
        self.assertEqual(status, 0, text)

    def test_check_fails_on_each_corruption(self):
        """A check that cannot fail is not a check. Each corruption must be caught, and for the
        right reason: the manifest's hashes are updated, so the hash check cannot mask it."""
        def mutated(name, blob_fn=None, line_fn=None):
            out = os.path.join(self.tmp, "mutant-" + name)
            shutil.copytree(self.out, out)
            with open(os.path.join(out, "stimulus.bin"), "rb") as f:
                blob = f.read()
            with open(os.path.join(out, "intent.jsonl")) as f:
                lines = [json.loads(line) for line in f]
            if blob_fn:
                blob = blob_fn(blob)
            if line_fn:
                self.assertTrue(line_fn(lines), f"{name}: nothing to corrupt")
            intent = "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
                             for r in lines).encode()
            manifest = copy.deepcopy(self.manifest)
            manifest["outputs"]["stimulus.bin"]["sha256"] = generate.sha256(blob)
            manifest["outputs"]["intent.jsonl"]["sha256"] = generate.sha256(intent)
            for fname, data in (("stimulus.bin", blob), ("intent.jsonl", intent),
                                ("manifest.json", json.dumps(manifest).encode())):
                with open(os.path.join(out, fname), "wb") as f:
                    f.write(data)
            return run_check(out)

        def flip(n):
            def fn(blob):
                protocols, chunks = container.unpack(blob)
                k = n % sum(len(d) for _, d in chunks)
                out = []
                for conn, data in chunks:
                    if 0 <= k < len(data):
                        data = data[:k] + bytes([data[k] ^ 0x01]) + data[k + 1:]
                    k -= len(data)
                    out.append((conn, data))
                return container.pack(out, protocols)
            return fn

        def other_protocol_for_connection_0(blob):
            protocols, chunks = container.unpack(blob)
            protocols[0] = "jt808" if protocols[0] == "gt06" else "gt06"
            return container.pack(chunks, protocols)

        def swap_first_two_chunks(blob):
            protocols, chunks = container.unpack(blob)
            i, j = [k for k, (c, _) in enumerate(chunks) if c == 0][:2]
            chunks[i], chunks[j] = chunks[j], chunks[i]
            return container.pack(chunks, protocols)

        def first(pred, edit):
            def fn(lines):
                for r in lines:
                    if pred(r):
                        edit(r)
                        return True
                return False
            return fn

        def clean(t):
            return lambda r: r.get("type") == t and r.get("fault") is None

        def set_(key, value):
            return lambda r: r.update({key: value})

        cases = {
            "flip a byte": dict(blob_fn=flip(0)),
            "flip another byte": dict(blob_fn=flip(4001)),
            "reorder two chunks": dict(blob_fn=swap_first_two_chunks),
            "the other protocol in the table": dict(blob_fn=other_protocol_for_connection_0),
            "a location's speed": dict(line_fn=first(clean("0x12"), lambda r: r["fields"].update(
                speed=(r["fields"]["speed"] + 1) % 256))),
            "a batch record": dict(line_fn=first(clean("0x0704"), lambda r: r["fields"]["records"][0]
                                                 .update(course=(r["fields"]["records"][0]["course"] + 1) % 360))),
            "a 0x5501 coordinate": dict(line_fn=first(clean("0x5501"), lambda r: r["fields"].update(
                lon=r["fields"]["lon"] ^ 1))),
            "bad checksum called clean": dict(line_fn=first(lambda r: r.get("fault") == "bad_checksum",
                                                            set_("fault", None))),
            "flag-lying called clean": dict(line_fn=first(lambda r: r.get("fault") == "flag_lying",
                                                          set_("fault", None))),
            "length disagreement called clean": dict(line_fn=first(
                lambda r: r.get("fault") == "length_disagreement", set_("fault", None))),
            "an escape count": dict(line_fn=first(lambda r: r.get("escapes", 0) > 0,
                                                  lambda r: r.update(escapes=r["escapes"] - 1))),
            "a serial number": dict(line_fn=first(clean("0x13"), lambda r: r.update(serial=r["serial"] + 1))),
            "a sync byte in no_sync garbage": dict(blob_fn=self.sync_byte_in_first_garbage()),
            "an IMEI that passes Luhn": dict(line_fn=first(
                lambda r: r.get("kind") == "connection" and r["protocol"] == "gt06",
                lambda r: r.update(device=r["device"][:14] + str(common.luhn_digit(r["device"][:14]))))),
        }
        for name, how in cases.items():
            status, text = mutated(name.replace(" ", "-"), **how)
            self.assertNotEqual(status, 0, f"{name}: the checker passed a corrupted stimulus")

    def sync_byte_in_first_garbage(self):
        """A blob edit: the first byte of the first garbage run becomes its protocol's sync byte."""
        protocol = {}
        with open(os.path.join(self.out, "intent.jsonl")) as f:
            for r in map(json.loads, f):
                if r["kind"] == "connection":
                    protocol[r["conn"]] = r["protocol"]
                elif r["kind"] == "garbage" and r["alphabet"] == "no_sync":
                    conn, offset = r["conn"], r["offset"]
                    break
        value = 0x78 if protocol[conn] == "gt06" else 0x7E

        def fn(blob):
            protocols, chunks = container.unpack(blob)
            pos, out = 0, []
            for c, data in chunks:
                if c == conn:
                    if pos <= offset < pos + len(data):
                        k = offset - pos
                        data = data[:k] + bytes([value]) + data[k + 1:]
                    pos += len(data)
                out.append((c, data))
            return container.pack(out, protocols)
        return fn

    def test_interleave_orders(self):
        p = coverage_params()
        p.update(connections=4, frames=40, assignment="equal")
        for mode in ("sequential", "round_robin"):
            p["interleave"] = mode
            conns, chunks = traffic.generate(p, SplitMix64(9))
            order = [c for c, _ in chunks]
            if mode == "sequential":
                self.assertEqual(order, sorted(order))
            else:
                self.assertEqual(order[:4], [0, 1, 2, 3])
                self.assertEqual(order[4:8], [0, 1, 2, 3])

    def test_readme_states_every_rule(self):
        with open(os.path.join(HERE, "README.md")) as f:
            readme = f.read()
        for rule in traffic.RULES:
            self.assertRegex(readme, rf"\b{rule}\b")


if __name__ == "__main__":
    unittest.main()
