import test from "node:test";
import assert from "node:assert/strict";
import {
  toBackendUpdateIngressPayload,
  toDomainIngressConfig,
  toDomainIngressStatus,
  toDomainIngressTriggerResult,
} from "./ingress.mapper.ts";

test("ingress.mapper: maps backend ingress config DTO to domain model", () => {
  const dto = {
    id: "cfg-1",
    household_id: "hh-100",
    user_id: "usr-200",
    provider: "gmail",
    is_enabled: true,
    interval_minutes: 30,
    last_run_at: "2026-11-17T10:00:00Z",
    next_run_at: "2026-11-17T10:30:00Z",
    status: "idle",
    last_error: null,
    created_at: "2026-11-01T00:00:00Z",
  };

  const domain = toDomainIngressConfig(dto);
  assert.equal(domain.id, "cfg-1");
  assert.equal(domain.householdId, "hh-100");
  assert.equal(domain.isEnabled, true);
  assert.equal(domain.intervalMinutes, 30);
  assert.equal(domain.lastRunAt, "2026-11-17T10:00:00Z");
});

test("ingress.mapper: maps backend status and trigger result", () => {
  const statusDto = {
    household_id: "hh-100",
    provider: "gmail",
    status: "idle",
    is_enabled: true,
    interval_minutes: 60,
    last_run_at: null,
    next_run_at: null,
    last_error: null,
    total_processed: 120,
    last_history_id: "hist-1234",
    last_email_internal_date: null,
    checkpoint_updated_at: null,
  };
  const status = toDomainIngressStatus(statusDto);
  assert.equal(status.totalProcessed, 120);
  assert.equal(status.lastHistoryId, "hist-1234");

  const triggerDto = {
    message: "Sync triggered",
    next_run_at: "2026-11-17T11:00:00Z",
    status: "triggered",
    config: {
      id: "cfg-1",
      household_id: "hh-100",
      user_id: "usr-200",
      provider: "gmail",
      is_enabled: true,
      interval_minutes: 15,
      last_run_at: null,
      next_run_at: "2026-11-17T11:00:00Z",
      status: "running",
      last_error: null,
      created_at: null,
    },
  };
  const trigger = toDomainIngressTriggerResult(triggerDto);
  assert.equal(trigger.message, "Sync triggered");
  assert.equal(trigger.config.status, "running");
});

test("ingress.mapper: converts update inputs to snake_case payload", () => {
  const payload = toBackendUpdateIngressPayload({
    intervalMinutes: 15,
    isEnabled: false,
  });
  assert.equal(payload.interval_minutes, 15);
  assert.equal(payload.is_enabled, false);
  assert.equal(payload.provider, "gmail");
});
