class CRC32:
    # Standard CRC32 constants
    CRC32_INIT = 0xFFFFFFFF
    CRC32_POLY = 0x04C11DB7

    _table = []
    _initialized = False

    @classmethod
    def _init_table(cls):
        """Generates the lookup table for 32-bit CRC."""
        cls._table = []
        for i in range(256):
            c = (i << 24) & 0xFFFFFFFF
            for _ in range(8):
                if c & 0x80000000:
                    c = ((c << 1) ^ cls.CRC32_POLY) & 0xFFFFFFFF
                else:
                    c = (c << 1) & 0xFFFFFFFF
            cls._table.append(c)
        cls._initialized = True

    @classmethod
    def init(cls):
        """Initializes the table if necessary and returns the initial CRC value."""
        if not cls._initialized:
            cls._init_table()
        return cls.CRC32_INIT

    @classmethod
    def update(cls, crc, data):
        """
        Updates the CRC value with new data.
        :param crc: Current CRC value
        :param data: bytes or bytearray
        :return: Updated 32-bit CRC value
        """
        if not cls._initialized:
            cls._init_table()

        for byte in data:
            # (crc >> 24) extract the top byte
            # ^ byte combines it with the incoming data byte
            lookup_index = ((crc >> 24) & 0xFF) ^ byte
            crc = ((crc << 8) ^ cls._table[lookup_index]) & 0xFFFFFFFF

        return crc


# --- Usage Example ---
if __name__ == "__main__":
    message = b"123456789"

    current_crc = CRC32.init()
    current_crc = CRC32.update(current_crc, message)

    print(f"CRC32 Result: {hex(current_crc).upper()}")