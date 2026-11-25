#include "crc32.h"

static uint32_t crc32_table[256];
static int table_initialized = 0;

static void init_crc32_table() {
    for (int i = 0; i < 256; i++) {
        uint32_t c = static_cast<uint32_t>(i) << 24;
        for (int j = 0; j < 8; j++) {
            c = (c & 0x80000000) ? ((c << 1) ^ CRC32_POLY) : (c << 1);
        }

        crc32_table[i] = c;
    }

    table_initialized = 1;
}

uint32_t crc32_init() {
    if (!table_initialized) {
        init_crc32_table();
    }

    return CRC32_INIT;
}

uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length) {
    if (!table_initialized) {
        init_crc32_table();
    }

    while (length--) {
        crc = (crc << 8) ^ crc32_table[((crc >> 24) & 0xFF) ^ *data++];
    }

    return crc;
}