// The interface between the harness and a decoder (decisions/0014). The harness owns the input,
// the count and the output. A decoder owns its connections' state, and the records it appends
// (records.h).

#ifndef DECODER_H
#define DECODER_H
#include <stdint.h>

// Printed as `detection`: the mode the image was built for (decisions/0007).
extern const char decoder_detection[];

// Bytes of state for `connections` connections. The harness gives it 16-byte-aligned memory.
uint32_t decoder_memory(uint32_t connections);

// Before the window: set up each connection from stimulus.bin's table, one protocol code per
// connection. This stands in for accepting a connection, before its first byte.
void decoder_init(void *memory, uint32_t connections, const uint8_t *protocols);

// Inside the window: one chunk of one connection's stream, in delivery order.
void decoder_chunk(uint32_t conn, const uint8_t *p, uint32_t n);

// Inside the window: the input has ended, and so has every connection's stream (0011, rule 7).
void decoder_end(void);

#endif
