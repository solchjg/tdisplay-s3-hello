// Composition root. FSD Phase 1: the 1 s uptime refresh on serial (FR-5.4,
// FR-5.5, FR-7.3), after the testbench boot marker (FR-7.6). No display yet.

#include <stdbool.h>
#include <stdint.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "hello_log.h"

static const char *TAG = "main";

#define REFRESH_MS 1000

void app_main(void)
{
    ESP_LOGI(TAG, "Init complete, running event-driven");

    // Absolute-time delay: the period does not drift with the work per tick.
    // N is taken from the clock once, then steps by exactly 1 (FR-5.5).
    TickType_t last = xTaskGetTickCount();
    uint32_t n = 0;
    for (bool first = true;; first = false) {
        xTaskDelayUntil(&last, pdMS_TO_TICKS(REFRESH_MS));
        n = first ? (uint32_t)(esp_timer_get_time() / 1000000) : n + 1;
        hello_log_up(n);
    }
}
