if(RHS_TEST_EEPROM)
    add_subdirectory(eeprom_test)
endif()

if(RHS_TEST_MEMMNG)
    add_subdirectory(memmng_test)
endif()

if(RHS_TEST_RECORDS)
    add_subdirectory(records_test)
endif()

if(RHS_TEST_FLASH_EX)
    add_subdirectory(flash_ex_test)
endif()
