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

if(RHS_TEST_IO)
    add_subdirectory(io_test)
endif()

if(RHS_TEST_EXTI)
    add_subdirectory(exti_test)
endif()

if(RHS_TEST_USB_BRIDGE OR RHS_TEST_USB_BRIDGE_APP)
    add_subdirectory(usb_bridge_test)
endif()

if(RHS_TEST_USB_MOUNT)
    add_subdirectory(usb_mount_test)
endif()
