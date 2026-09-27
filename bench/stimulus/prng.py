"""SplitMix64: the generator's only source of randomness.

A stimulus is versioned as generator + parameters + seed (bench/SPEC.md §8), so nothing in it may
depend on the Python version. The helpers in Python's `random` module have changed between CPython
releases. This generator is small enough to carry, and every draw below is integer arithmetic.

SplitMix64 is Steele, Lea and Flood's generator (OOPSLA 2014), in Vigna's reference form,
https://prng.di.unimi.it/splitmix64.c. test_stimulus.py checks it against 50 outputs of that
reference implementation.
"""

MASK64 = (1 << 64) - 1
PPM = 1_000_000


class SplitMix64:
    def __init__(self, seed):
        if not 0 <= seed <= MASK64:
            raise ValueError(f"seed must be a 64-bit unsigned integer, got {seed}")
        self.state = seed

    def next64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def below(self, n):
        """A uniform integer in [0, n). Rejection sampling, so no value is favoured."""
        if n < 1:
            raise ValueError(f"below({n})")
        limit = (1 << 64) - (1 << 64) % n  # the largest multiple of n that fits
        while True:
            x = self.next64()
            if x < limit:
                return x % n

    def between(self, lo, hi):
        """A uniform integer in [lo, hi], both ends included."""
        return lo + self.below(hi - lo + 1)

    def chance(self, ppm):
        """True with probability ppm / 1,000,000."""
        return self.below(PPM) < ppm

    def pick(self, weights):
        """A key of `weights` (name -> integer weight), chosen in proportion to its weight.

        Keys are visited in sorted order, so the order of keys in a parameter file cannot change
        which one is drawn."""
        items = [(k, w) for k, w in sorted(weights.items()) if w > 0]
        r = self.below(sum(w for _, w in items))
        for k, w in items:
            if r < w:
                return k
            r -= w
        raise AssertionError("unreachable")

    def digits(self, n):
        """n decimal digits, as a string."""
        return "".join(str(self.below(10)) for _ in range(n))

    def bytes_from(self, n, alphabet):
        """n bytes, each drawn uniformly from `alphabet` (a bytes object)."""
        return bytes(alphabet[self.below(len(alphabet))] for _ in range(n))
