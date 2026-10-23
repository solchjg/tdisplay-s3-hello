// Composition root. Skeleton: proves the build pipeline and emits the
// testbench boot marker (FSD FR-7.6); implements nothing else yet.

#include "esp_log.h"

static const char *TAG = "main";

void app_main(void)
{
    ESP_LOGI(TAG, "Init complete, running event-driven");
}
