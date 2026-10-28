// SPDX-License-Identifier: Apache-2.0
// Read-only recovery slot report. Deliberately exposes no mutating HAL methods.
#include <BootControlClient.h>
#include <cstdio>
int main() {
    const auto client = android::hal::BootControlClient::WaitForService();
    if (!client) { std::fputs("Boot HAL unavailable\n", stderr); return 1; }
    const int slots = client->GetNumSlots();
    const int current = client->GetCurrentSlot();
    const int active = client->GetActiveBootSlot();
    if (slots != 2 || current < 0 || current >= slots || active < 0 || active >= slots) {
        std::fprintf(stderr, "Invalid slot report: slots=%d current=%d active=%d\n", slots, current, active);
        return 2;
    }
    std::printf("{\"slots\":%d,\"current\":%d,\"active\":%d,\"merge_status\":%d,\"slot_state\":[",
                slots, current, active, static_cast<int>(client->getSnapshotMergeStatus()));
    for (int slot = 0; slot < slots; ++slot) {
        const auto suffix = client->GetSuffix(slot);
        const auto bootable = client->IsSlotBootable(slot);
        const auto successful = client->IsSlotMarkedSuccessful(slot);
        if (suffix != (slot == 0 ? "_a" : "_b") || !bootable || !successful) {
            std::fputs("Invalid slot suffix or failed status RPC\n", stderr); return 3;
        }
        std::printf("%s{\"slot\":%d,\"suffix\":\"%s\",\"bootable\":%s,\"successful\":%s}",
                    slot ? "," : "", slot, suffix.c_str(), *bootable ? "true" : "false", *successful ? "true" : "false");
    }
    std::puts("]}");
    return 0;
}
