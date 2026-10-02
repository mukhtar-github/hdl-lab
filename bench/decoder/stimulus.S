# stimulus.bin's bytes, linked into the image as data the compiler cannot see (decisions/0014).
# The Makefile copies the file into the build directory, and assembles this file with that
# directory on the assembler's search path, so .incbin finds it there.
    .section .stimulus, "a"
    .balign 16
    .globl stimulus
stimulus:
    .incbin "stimulus.bin"
