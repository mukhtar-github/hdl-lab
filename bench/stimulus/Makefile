# ============================================================
# bench/stimulus — the stimulus generator (README.md)
#
#   make            generate the coverage stimulus, then check it
#   make test       the unit tests: anchors, layouts, parameters, streams
#   make clean
#
#   make PARAMS=<file> SEED=<n>     any parameter file, any seed
#
# The coverage file exists to exercise every class in bench/SPEC.md
# §1-5. No value in it is a claim about traffic, so no result may be
# quoted from a stimulus made with it.
# ============================================================

PYTHON := python3
PARAMS := params/coverage.json
SEED   := 1
OUT    := build/$(basename $(notdir $(PARAMS)))-$(SEED)

.PHONY: all check test clean

all: check

check:
	@$(PYTHON) generate.py --params $(PARAMS) --seed $(SEED) --out $(OUT)
	@$(PYTHON) check.py $(OUT)

test:
	@$(PYTHON) -m unittest test_stimulus

clean:
	rm -rf build
