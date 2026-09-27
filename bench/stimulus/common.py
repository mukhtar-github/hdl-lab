"""Helpers shared by the GT06 and JT808 encoders: BCD, the device clock, identifiers.

Citations name the pinned sources in reference/README.md:
  [doc]      GT06 GPS Tracker Communication Protocol v1.8.1 (Concox); "p." is the PDF page
  [traccar]  Traccar 847edd2c, org/traccar/protocol/ unless another directory is given
"""

import datetime

# Rule R5 (README): every device clock starts at a random second of 2026. Only the encoding of the
# time matters to a decoder, so the year is arbitrary. It is fixed so that two runs agree.
EPOCH = datetime.datetime(2026, 1, 1)
YEAR_SECONDS = 365 * 24 * 3600


def bcd(digits):
    """Pack an even number of decimal digits, two per byte, most significant first."""
    if len(digits) % 2 or not digits.isdigit():
        raise ValueError(f"BCD needs an even number of decimal digits, got {digits!r}")
    return bytes(int(digits[i:i + 2], 16) for i in range(0, len(digits), 2))


def clock(seconds):
    """(yy, mm, dd, hh, mi, ss) at `seconds` after EPOCH."""
    t = EPOCH + datetime.timedelta(seconds=seconds)
    return t.year % 100, t.month, t.day, t.hour, t.minute, t.second


def clock_digits(seconds):
    """The same instant as 12 digits, YYMMDDhhmmss: how every record states a time."""
    return "".join(f"{v:02d}" for v in clock(seconds))


def luhn_digit(digits):
    """The Luhn check digit for a string of digits, as [traccar] helper/Checksum.java:214-232
    computes it: from the right, double every other digit starting with the rightmost."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10


def fake_imei(rng):
    """15 digits whose last digit is deliberately NOT the Luhn check digit of the first 14.

    [traccar] Jt808ProtocolDecoder.java:277 forms an IMEI by appending exactly that check digit,
    so a number that fails it is not a valid IMEI and cannot belong to any device. bench/README
    rule 2a: GT06 identifies devices by cleartext IMEI."""
    body = rng.digits(14)
    return body + str((luhn_digit(body) + rng.between(1, 9)) % 10)


def fake_terminal(rng):
    """A JT808 terminal number: 12 digits, always beginning 00000.

    Only its encoding matters to a decoder ([traccar] Jt808ProtocolDecoder.java:270-279 reads a BCD
    ID as its digit string). The fixed prefix keeps it from resembling a subscriber number."""
    return "00000" + rng.digits(7)
