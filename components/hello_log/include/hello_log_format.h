// Serial Log Interface, pure format core (FSD §7.2). No ESP-IDF headers, so
// the host tier compiles it as is.
#pragma once

#include <stddef.h>
#include <stdint.h>

// Longest message body in §7.2 plus the terminator.
#define HELLO_LOG_LINE_MAX 48

// Writes "up=<n>" (FSD FR-7.3): decimal, no padding, no sign.
void hello_log_format_up(char *buf, size_t len, uint32_t n);
