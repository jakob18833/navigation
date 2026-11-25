#ifndef CRC32_H
#define CRC32_H

#include <cstdint>
#include <cstddef>

#define CRC32_INIT 0xFFFFFFFF
#define CRC32_POLY 0x04C11DB7

uint32_t crc32_init();

uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length);

#endif