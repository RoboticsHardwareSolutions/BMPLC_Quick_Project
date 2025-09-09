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
