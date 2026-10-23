#include "hello_log.h"

#include "esp_log.h"
#include "hello_log_format.h"

static const char *TAG = "hello";

void hello_log_up(uint32_t n)
{
    char line[HELLO_LOG_LINE_MAX];
    hello_log_format_up(line, sizeof line, n);
    ESP_LOGI(TAG, "%s", line);
}
