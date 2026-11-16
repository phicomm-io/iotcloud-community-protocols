# Sensor sample age and PM power saving

The additive `sensor-values-v3` contract documents current MessagePack schema 3 split metadata/state and the native LAN v3 PM extension. Status is `implemented-unreleased`; accuracy and power require board-specific device validation. Frozen schema 2 artifacts remain unchanged.

[Machine contract](contracts/sensor-values-v3.json) · [State schema](contracts/schemas/sensor-values-v3.schema.json) · [Metadata schema](contracts/schemas/sensor-metadata-v3.schema.json) · [Examples](contracts/examples/sensor-values-v3.json)

Metadata uses `phicomm/v2/<scope>/sensor/<device_id>/metadata` and may be retained; state uses the same prefix with `/state` and must be live, non-retained. Both contain schema 3, canonical device ID, nonzero boot and descriptor_revision; state also contains nonzero sequence. Metadata fields contain name/type/unit; state sensors contain value/valid/age_ms and the optional limit below. Bind current descriptors before accepting complete snapshots with existing boot/sequence rules. Missing, invalid, unknown-typed or mismatching-unit fields revoke old numeric candidates; valid siblings remain independent.

## Separate sample and communication limits

Only numeric `pm25`/`pm10` fields may carry `max_age_ms`: a strict integer from 1 through 3600000, with metadata unit `µg/m³`. Absence retains the existing short limit. DAIKIN G1/G2 publishes 120000 in ordinary dynamic mode and 3600000 during enabled night saving. Actual source age never resets on publish, query or reconnect. Validity requires both:

- Source age plus receiver elapsed time is strictly below the sample limit.
- Time since reception is below the existing communication lease: fifteen seconds for A1, at most twenty seconds for web/M1, or a shorter configured lease.

Schema checks types and absolute bounds. Runtime checks enforce age below the selected limit, descriptor unit binding, replay prevention and communication freshness. MQTT availability, sessions and HA publication expiry remain independent. Repeated sequence, retired boot and retained state cannot renew a lease. Sample expiry, explicit module faults and invalid new samples invalidate values instead of synthesizing zero. M1 MCU display leases use the smaller remaining sample/communication lease; UART is unchanged.

## UDP and compatibility

The [LAN sample body schema](contracts/schemas/lan-pm-age-v1.schema.json) adds optional `pm25_max_age_ms` to native LAN v3 body. `ages[2]` retains real PM2.5 age. The five slots remain temperature, humidity, PM2.5, formaldehyde and CO₂; there is no PM10 slot. Packet identity, token, permissions and replay rules stay unchanged. Older strict consumers may reject extended fields; update linked consumers before enabling long cycles. Messages without the extension retain existing behavior.

## Night PM settings

The [configuration schema](contracts/schemas/daikin-pm-power-v1.schema.json) uses existing `config.set`, section `pm_power`, with complete values: enabled (boolean), start_minute/end_minute (0..1439), timezone_minutes (−720..840). Defaults are false, 1380, 420, 480. Unknown/out-of-range inputs use existing invalid_params, persistence errors storage_error, with existing authentication/configuration transactions. status.get/config.get return these four settings in pm_power; G3 does not expose this capability.

Use local half-open [start,end), allowing midnight crossing. Equal endpoints disable the interval; an untrusted clock keeps dynamic measurement. Startup and daytime use mode 5. Night uses 59000 ms policy steps, enabling mode 5 for one step every sixty steps and mode 1 otherwise. Wait at least thirty-six seconds after enabling, then accept only a complete checksum-correct finished response before advancing the sample timestamp. Leaving night restores mode 5 and the ordinary 120-second sample limit. Report actual age and communication status throughout.

Retain raw PM, CO₂, formaldehyde and climate inputs separately in diagnostics; all business outputs use the same compensated results. SGP30 baseline is sensor-bound private cache, excluded from transferable user configuration; preserve on Wi-Fi reset and clear on full factory reset.
