cmake_minimum_required(VERSION 3.24)
project(cdc_net_hello_rhs C)
set(CMAKE_C_STANDARD 11)

# --- Mongoose packed FS ---
set(MONGOOSE_DIR ${CMAKE_SOURCE_DIR}/thirdparty/mongoose)
set(PACK_TOOL ${CMAKE_CURRENT_BINARY_DIR}/pack_tool)
set(PACKED_FS_C ${CMAKE_CURRENT_BINARY_DIR}/packed_fs.c)

file(GLOB_RECURSE DIST_FILES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/dist/*.html
    ${CMAKE_CURRENT_SOURCE_DIR}/dist/*.css
    ${CMAKE_CURRENT_SOURCE_DIR}/dist/*.js
)

# Build the pack tool for the host (not the cross-compiler)
add_custom_command(
    OUTPUT ${PACK_TOOL}
    COMMAND cc -o ${PACK_TOOL} ${MONGOOSE_DIR}/test/pack.c
    DEPENDS ${MONGOOSE_DIR}/test/pack.c
    COMMENT "Building mongoose pack tool"
)

# Run pack to embed dist/ files as C byte arrays
add_custom_command(
    OUTPUT ${PACKED_FS_C}
    COMMAND ${PACK_TOOL} -s ${CMAKE_CURRENT_SOURCE_DIR}/ ${DIST_FILES} > ${PACKED_FS_C}
    DEPENDS ${PACK_TOOL} ${DIST_FILES}
    COMMENT "Packing web files -> packed_fs.c"
)

# Named target so other targets can declare a build-order dependency on it.
add_custom_target(generate_packed_fs DEPENDS ${PACKED_FS_C})

# Inject packed_fs.c into the mongoose library itself so that
# mg_unpack / mg_unlist are defined where mongoose.c.obj references them.
target_sources(mongoose PRIVATE ${PACKED_FS_C})

# Guarantee generation runs before mongoose is compiled (cross-dir dependency).
add_dependencies(mongoose generate_packed_fs)

add_library(${PROJECT_NAME} STATIC
    cdc_net_hello_rhs.c
)

target_link_libraries(
    ${PROJECT_NAME}
    PUBLIC
    cdc_net
)

start_up(cdc_net_hello_rhs_start_up)
