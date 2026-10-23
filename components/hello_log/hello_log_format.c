#include "hello_log_format.h"

#include <inttypes.h>
#include <stdio.h>

void hello_log_format_up(char *buf, size_t len, uint32_t n)
{
    snprintf(buf, len, "up=%" PRIu32, n);
}
