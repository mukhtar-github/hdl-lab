// Text output, after the window only. Every byte leaves through the syscall proxy's SYS_write, one
// buffer at a time (decisions/0014, section 5). One character a command would cost 5,000
// instructions under Spike (docs/results/20260930T052623Z-spike-htif-cost).

#ifndef OUTPUT_H
#define OUTPUT_H
#include <stdint.h>

void out_char(char c);
void out_str(const char *s);
void out_u32(uint32_t v);
void out_i32(int32_t v);
void out_u64(uint64_t v);
void out_hex(const uint8_t *p, uint32_t nibbles);  // the last `nibbles` digits, as records.h stores them
void out_flush(void);                              // write what is buffered; exit 5 if the host refuses

#endif
