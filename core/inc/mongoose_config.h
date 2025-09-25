// If we could guess an MG_ARCH so far, preserve it, otherwise try GCC-based
#if defined(MG_ARCH)
#    define MG_STMPACK_ARCH MG_ARCH
#    undef MG_ARCH
#elif defined(__GNUC__)
#    define MG_STMPACK_ARCH MG_ARCH_NEWLIB
#endif

#define MG_ARCH MG_ARCH_FREERTOS
