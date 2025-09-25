# [0.1.2] - 2025-09-20

### Refactor
- Migrated from LWIP to Mongoose network stack for ethernet functionality
  - Removed LWIP submodule and dependencies
  - Added Mongoose library integration for STM32F7 ethernet driver
  - Updated device templates to use `RHS_SERVICE_ETH_NET` instead of `RHS_SERVICE_LWIP`
  - Added Mongoose configuration file for STM32F7 platform

### Update
- Updated RHS subproject to latest version (commit 2c1c5f8)
- Removed unused `RHS_HAL_NETWORK` and `RHS_CAN_OPEN` flags from device templates
- Cleaned up CMakeLists.txt to conditionally build Mongoose based on service requirements

# [0.1.1] - 2025-09-09

### Feature
- Added TinyUSB library integration
- Implemented dual CDC (Communication Device Class) functionality
- Added RNDIS (Remote Network Driver Interface Specification) support

### Refactor
- Removed libusb_stm32 submodule and replaced with TinyUSB
- Refactored USB configuration and HAL settings
- Reorganized CMakeLists.txt structure for better USB library management
- Updated service settings for USB serial bridge
- Simplified device template configurations by removing conditional compilation flags
- Added RHS_TEST_RECORDS test to all device templates

### Update
- Updated rhs subproject to latest version
- Updated rcan, mongoose subproject commits
- Added USB string descriptor indices configuration

# [0.1.0] 

### Feature
- Fix launch.json for all BMPLCs
- Added run time and stack control for threads in FreeRTOSConfig.h
- Added CHANGELOG.md
