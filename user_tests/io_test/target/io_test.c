#include "rhs.h"
#include "rhs_hal.h"
#include "cli.h"


/**
 * @file input_app.c
 * @brief Input service with CLI commands for controlling KEYs and OUTs, and reading INs
 *
 * Available CLI commands:
 * - io: Universal IO control command
 *   Usage:
 *     io                        - Read all input states (IN0-IN4)
 *     io <-key[0-4]> <on|off>   - Control keys (KEY0-KEY4)
 *     io <-out[0-4]> <on|off>   - Control outputs (OUT0-OUT4)
 *     io ?                      - Show help
 *   Examples:
 *     io                        - Show all input states
 *     io -key0 on               - Turn KEY0 ON
 *     io -out1 off              - Turn OUT1 OFF
 *     io ?                      - Show help
 */

// Function pointer arrays for IO control
typedef void (*io_control_func_t)(void);
typedef bool (*input_read_func_t)(void);

// Arrays of function pointers for keys and outputs
static const io_control_func_t key_on_funcs[]  = {KEY0_ON, KEY1_ON, KEY2_ON, KEY3_ON, KEY4_ON};
static const io_control_func_t key_off_funcs[] = {KEY0_OFF, KEY1_OFF, KEY2_OFF, KEY3_OFF, KEY4_OFF};
static const io_control_func_t out_on_funcs[]  = {OUT0_ON, OUT1_ON, OUT2_ON, OUT3_ON, OUT4_ON};
static const io_control_func_t out_off_funcs[] = {OUT0_OFF, OUT1_OFF, OUT2_OFF, OUT3_OFF, OUT4_OFF};
static const input_read_func_t input_funcs[]   = {IN0_IS_HIGH, IN1_IS_HIGH, IN2_IS_HIGH, IN3_IS_HIGH, IN4_IS_HIGH};

static const char* key_names[]   = {"KEY0", "KEY1", "KEY2", "KEY3", "KEY4"};
static const char* out_names[]   = {"OUT0", "OUT1", "OUT2", "OUT3", "OUT4"};
static const char* input_names[] = {"IN0", "IN1", "IN2", "IN3", "IN4"};

#define MAX_IO_COUNT COUNT_OF(key_on_funcs)

// Static assertions to ensure all arrays have the same size
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(key_off_funcs),
               "key_on_funcs and key_off_funcs must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(out_on_funcs),
               "key_on_funcs and out_on_funcs must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(out_off_funcs),
               "key_on_funcs and out_off_funcs must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(input_funcs), "key_on_funcs and input_funcs must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(key_names), "key_on_funcs and key_names must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(out_names), "key_on_funcs and out_names must have the same size");
_Static_assert(COUNT_OF(key_on_funcs) == COUNT_OF(input_names), "key_on_funcs and input_names must have the same size");

struct IoApp
{
    Cli* cli;
};

/**
 * @brief Parse IO command and extract type, index and state
 * @param args Command arguments string
 * @param io_type Output parameter for IO type ('k' for key, 'o' for out)
 * @param index Output parameter for IO index (0-4)
 * @param is_on Output parameter for state (true for on, false for off)
 * @return true if parsing successful, false otherwise
 */
static bool parse_io_command(const char* args, char* io_type, int* index, bool* is_on)
{
    if (args == NULL)
        return false;

    // Find space separator
    const char* space = strchr(args, ' ');
    if (space == NULL || *(space + 1) == 0)
        return false;

    // Parse IO type and index (e.g., "key0" or "out2")
    if (strncmp(args, "key", 3) == 0 && args[3] >= '0' && args[3] <= '4')
    {
        *io_type = 'k';
        *index   = args[3] - '0';
    }
    else if (strncmp(args, "out", 3) == 0 && args[3] >= '0' && args[3] <= '4')
    {
        *io_type = 'o';
        *index   = args[3] - '0';
    }
    else
    {
        return false;
    }

    // Parse state (on/off)
    const char* state_str = space + 1;
    if (strcmp(state_str, "on") == 0)
    {
        *is_on = true;
    }
    else if (strcmp(state_str, "off") == 0)
    {
        *is_on = false;
    }
    else
    {
        return false;
    }

    return true;
}

void io_test(char* args, void* context)
{
    // Show help if user enters '?' or 'help'
    if (args != NULL && (strcmp(args, "?") == 0 || strcmp(args, "help") == 0))
    {
        printf("IO Control Commands:\n");
        printf("Usage:\n");
        printf("  io                        - Read all input states\n");
        printf("  io <key[0-4]> <on|off>   - Control keys\n");
        printf("  io <out[0-4]> <on|off>   - Control outputs\n");
        printf("  io ?                      - Show this help\n");
        printf("Examples:\n");
        printf("  io key0 on\n");
        printf("  io out1 off\n");
        return;
    }

    // If no arguments provided, read all inputs
    if (args == NULL)
    {
        printf("Input states:\n");
        for (int i = 0; i < MAX_IO_COUNT; i++)
        {
            printf("  %s: %s\n", input_names[i], input_funcs[i]() ? "HIGH" : "LOW");
        }
        return;
    }

    // Parse control command
    char io_type;
    int  index;
    bool is_on;

    if (!parse_io_command(args, &io_type, &index, &is_on))
    {
        printf("Invalid argument: %s\n", args);
        printf("Type 'io ?' for help\n");
        return;
    }

    // Validate index range
    if (index < 0 || index >= MAX_IO_COUNT)
    {
        printf("Invalid index: %d. Valid range is 0-%d\n", index, MAX_IO_COUNT - 1);
        return;
    }

    // Execute the appropriate function
    if (io_type == 'k')
    {
        if (is_on)
        {
            key_on_funcs[index]();
            printf("%s turned ON\n", key_names[index]);
        }
        else
        {
            key_off_funcs[index]();
            printf("%s turned OFF\n", key_names[index]);
        }
    }
    else if (io_type == 'o')
    {
        if (is_on)
        {
            out_on_funcs[index]();
            printf("%s turned ON\n", out_names[index]);
        }
        else
        {
            out_off_funcs[index]();
            printf("%s turned OFF\n", out_names[index]);
        }
    }
}




void rhs_io_test(void)
{
    Cli* cli = rhs_record_open(RECORD_CLI);
    cli_add_command(cli, "io", io_test, NULL);
    rhs_record_close(RECORD_CLI);
}
