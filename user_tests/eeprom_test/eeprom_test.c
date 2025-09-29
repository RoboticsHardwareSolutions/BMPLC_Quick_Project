#include "rhs.h"
#include "rhs_hal.h"
#include "runit.h"
#include "cli.h"
#include "eeprom.h"

#define TEST_RECORD_NAME "test_eeprom"

/* EEPROM instance for testing */
static EepromType at24c256;

void eeprom_full_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Start counter from a random value
    uint8_t start_value = (uint8_t) (rhs_hal_random_get() & 0xFF);

    // Write all pages
    for (size_t i_page = 0; i_page < (at24c256.size / at24c256.page_size); ++i_page)
    {
        uint8_t page_buf[64];

        // Fill page buffer
        for (size_t page_byte = 0; page_byte < at24c256.page_size; ++page_byte)
        {
            uint8_t byte        = (start_value + (i_page * at24c256.page_size) + page_byte) % 256;
            page_buf[page_byte] = byte;
        }

        uint16_t page_addr = i_page * at24c256.page_size;
        status             = eeprom_write(&at24c256, page_addr, page_buf, at24c256.page_size);
        runit_assert(status == EepromStatusOk);
    }

    // Read and verify all pages
    for (size_t i_page = 0; i_page < (at24c256.size / at24c256.page_size); ++i_page)
    {
        uint8_t  page_buf[64];
        uint16_t page_addr = i_page * at24c256.page_size;

        status = eeprom_read(&at24c256, page_addr, page_buf, at24c256.page_size);
        runit_assert(status == EepromStatusOk);

        for (size_t page_byte = 0; page_byte < at24c256.page_size; ++page_byte)
        {
            uint8_t expected = (start_value + (i_page * at24c256.page_size) + page_byte) % 256;
            runit_eq(expected, page_buf[page_byte]);
        }
    }
}

void eeprom_overwrite_first3bytes_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Generate a random address within EEPROM range, aligned to 3 bytes
    uint16_t rand_addr = (uint16_t) (rhs_hal_random_get() % (at24c256.size - 3));
    rand_addr &= ~0x03;  // align to 4 for safety

    uint8_t write_ff[3] = {0xFF, 0xFF, 0xFF};
    uint8_t read_buf[3] = {0};

    // Write 0xFF to 3 bytes at random address
    status = eeprom_write(&at24c256, rand_addr, write_ff, 3);
    runit_assert(status == EepromStatusOk);

    // Read back 3 bytes at random address
    status = eeprom_read(&at24c256, rand_addr, read_buf, 3);
    runit_assert(status == EepromStatusOk);
    runit_eq(read_buf[0], 0xFF);
    runit_eq(read_buf[1], 0xFF);
    runit_eq(read_buf[2], 0xFF);

    // Write 0xAA to first byte
    uint8_t write_aa = 0xAA;
    status           = eeprom_write(&at24c256, rand_addr, &write_aa, 1);
    runit_assert(status == EepromStatusOk);

    // Write 0x55 to third byte (rand_addr + 2)
    uint8_t write_55 = 0x55;
    status           = eeprom_write(&at24c256, rand_addr + 2, &write_55, 1);
    runit_assert(status == EepromStatusOk);

    // Read back 3 bytes at random address
    status = eeprom_read(&at24c256, rand_addr, read_buf, 3);
    runit_assert(status == EepromStatusOk);
    runit_eq(read_buf[0], 0xAA);
    runit_eq(read_buf[1], 0xFF);
    runit_eq(read_buf[2], 0x55);
}

void eeprom_partial_page_write_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Select a random page
    uint16_t page_idx  = (uint16_t) (rhs_hal_random_get() % (at24c256.size / at24c256.page_size));
    uint16_t page_addr = page_idx * at24c256.page_size;

    // Select a random position within the page to start writing
    uint8_t start_offset = (uint8_t) (rhs_hal_random_get() % at24c256.page_size);
    uint8_t write_len    = (uint8_t) (rhs_hal_random_get() % (at24c256.page_size - start_offset));
    if (write_len == 0)
        write_len = 1;  // at least one byte

    // Erase the page (write 0xFF)
    uint8_t erase_buf[64];
    memset(erase_buf, 0xFF, at24c256.page_size);
    status = eeprom_write(&at24c256, page_addr, erase_buf, at24c256.page_size);
    runit_assert(status == EepromStatusOk);

    // Prepare random data for writing
    uint8_t rand_data[64];
    for (uint8_t i = 0; i < write_len; ++i)
        rand_data[i] = (uint8_t) (rhs_hal_random_get() & 0xFF);

    // Write random data starting from start_offset
    uint16_t write_addr = page_addr + start_offset;
    status              = eeprom_write(&at24c256, write_addr, rand_data, write_len);
    runit_assert(status == EepromStatusOk);

    // Read the whole page
    uint8_t read_buf[64] = {0};
    status               = eeprom_read(&at24c256, page_addr, read_buf, at24c256.page_size);
    runit_assert(status == EepromStatusOk);

    // Check that all bytes before start_offset are 0xFF
    for (uint8_t i = 0; i < start_offset; ++i)
        runit_eq(read_buf[i], 0xFF);

    // Check that written data matches
    for (uint8_t i = 0; i < write_len; ++i)
        runit_eq(read_buf[start_offset + i], rand_data[i]);

    // Check that all bytes after written data are 0xFF
    for (uint8_t i = start_offset + write_len; i < at24c256.page_size; ++i)
        runit_eq(read_buf[i], 0xFF);
}

void eeprom_page_boundary_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Try to write across page boundary - should fail
    uint16_t page_idx   = (uint16_t) (rhs_hal_random_get() % ((at24c256.size / at24c256.page_size) - 1));
    uint16_t page_addr  = page_idx * at24c256.page_size;
    uint16_t cross_addr = page_addr + at24c256.page_size - 10;  // 10 bytes before page end

    uint8_t cross_data[20];  // 20 bytes - will cross page boundary
    for (uint8_t i = 0; i < 20; ++i)
        cross_data[i] = i;

    // This should now succeed because function handles page boundaries automatically
    status = eeprom_write(&at24c256, cross_addr, cross_data, 20);
    runit_assert(status == EepromStatusOk);

    // Verify the data was written correctly across page boundary
    uint8_t read_buf[20];
    status = eeprom_read(&at24c256, cross_addr, read_buf, 20);
    runit_assert(status == EepromStatusOk);

    for (uint8_t i = 0; i < 20; ++i)
        runit_eq(read_buf[i], cross_data[i]);
}

void eeprom_size_limit_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Try to write more than page size - should now succeed (automatic page handling)
    uint8_t large_data[128];  // Larger than page size (64)
    for (uint8_t i = 0; i < 128; ++i)
        large_data[i] = i;

    status = eeprom_write(&at24c256, 0, large_data, 128);
    runit_assert(status == EepromStatusOk);

    // Verify the large data was written correctly
    uint8_t read_large[128];
    status = eeprom_read(&at24c256, 0, read_large, 128);
    runit_assert(status == EepromStatusOk);

    for (uint8_t i = 0; i < 128; ++i)
        runit_eq(read_large[i], large_data[i]);

    // Try to write beyond EEPROM size - should fail
    uint8_t small_data[10];
    for (uint8_t i = 0; i < 10; ++i)
        small_data[i] = i;

    status = eeprom_write(&at24c256, at24c256.size - 5, small_data, 10);
    runit_assert(status == EepromStatusInvalidParam);

    // This should succeed - write at valid address with valid size
    status = eeprom_write(&at24c256, at24c256.size - 10, small_data, 10);
    runit_assert(status == EepromStatusOk);
}

void eeprom_random_access_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;

    // Test random write/read operations
    for (int test_iter = 0; test_iter < 10; ++test_iter)
    {
        // Generate random address and size (can now cross page boundaries)
        uint16_t rand_addr = (uint16_t) (rhs_hal_random_get() % (at24c256.size - 128));
        uint8_t  rand_size = (uint8_t) ((rhs_hal_random_get() % 128) + 1);  // 1-128 bytes

        // Only ensure we don't exceed EEPROM size
        if (rand_addr + rand_size > at24c256.size)
            rand_size = at24c256.size - rand_addr;

        // Generate random data
        uint8_t write_data[128];  // Increased to match maximum possible rand_size
        for (uint8_t i = 0; i < rand_size; ++i)
            write_data[i] = (uint8_t) (rhs_hal_random_get() & 0xFF);

        // Write data
        status = eeprom_write(&at24c256, rand_addr, write_data, rand_size);
        runit_assert(status == EepromStatusOk);

        // Read back and verify
        uint8_t read_data[128];  // Increased to match maximum possible rand_size
        status = eeprom_read(&at24c256, rand_addr, read_data, rand_size);
        runit_assert(status == EepromStatusOk);

        for (uint8_t i = 0; i < rand_size; ++i)
            runit_eq(read_data[i], write_data[i]);
    }
}

void eeprom_multi_page_write_test(void)
{
    if (!rhs_hal_i2c_is_device_ready(&rhs_hal_i2c1_handle, 0x50, 100))
    {
        printf("no device connected, skipping\r\n");
        return;
    }

    EepromStatus status;
    
    // Choose a random address and write across multiple pages
    uint16_t start_addr = (uint16_t)(rhs_hal_random_get() % (at24c256.size - 200));
    uint16_t write_len = 150; // More than 2 pages (64*2 = 128)

    // Prepare test data
    uint8_t write_data[200];
    for (uint16_t i = 0; i < write_len; ++i)
        write_data[i] = (uint8_t)((rhs_hal_random_get() + i) & 0xFF);

    // Write data across multiple pages
    status = eeprom_write(&at24c256, start_addr, write_data, write_len);
    runit_assert(status == EepromStatusOk);

    // Read back and verify
    uint8_t read_data[200];
    status = eeprom_read(&at24c256, start_addr, read_data, write_len);
    runit_assert(status == EepromStatusOk);

    for (uint16_t i = 0; i < write_len; ++i)
        runit_eq(read_data[i], write_data[i]);
}

void eeprom_test(char* args, void* context)
{
    runit_counter_assert_passes   = 0;
    runit_counter_assert_failures = 0;

    // Configure EEPROM instance
    at24c256.i2c_handle     = &rhs_hal_i2c1_handle;
    at24c256.i2c_address    = 0x50;
    at24c256.size           = 32768;
    at24c256.page_size      = 64;
    at24c256.address_size   = 2;
    at24c256.write_delay_ms = 6;
    at24c256.timeout_ms     = 100;

    // Initialize I2C interface
    rhs_hal_i2c_init(&rhs_hal_i2c1_handle);
    rhs_hal_i2c_acquire(&rhs_hal_i2c1_handle);

    // Initialize EEPROM library
    EepromStatus status = eeprom_init(&at24c256);
    runit_assert(status == EepromStatusOk);

    // Run tests
    eeprom_overwrite_first3bytes_test();
    eeprom_partial_page_write_test();
    eeprom_page_boundary_test();
    eeprom_size_limit_test();
    eeprom_multi_page_write_test();
    eeprom_random_access_test();
    // eeprom_full_test(); // Uncomment for full EEPROM test (takes longer)

    
    rhs_hal_i2c_release(&rhs_hal_i2c1_handle);
    rhs_hal_i2c_deinit(&rhs_hal_i2c1_handle);

    runit_report();
}

void rhs_eeprom_test(void)
{
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "eeprom_test", eeprom_test, NULL);
    rhs_record_close(RECORD_CLI);
}