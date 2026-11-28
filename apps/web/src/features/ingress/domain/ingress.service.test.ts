import test from "node:test";
import assert from "node:assert/strict";
import {
  formatFriendlyDateTime,
  formatFriendlyNextRun,
  formatIntervalLabel,
  formatPresetIntervalLabel,
  getEmailConnectionStatus,
  getExecutionStatusBadge,
  getStatusColor,
  isValidInterval,
  sanitizeErrorMessage,
} from "./ingress.service.ts";
import type { IngressConfig, IngressStatus } from "./ingress.model.ts";

test("ingress.service: formatIntervalLabel formats standard intervals", () => {
  assert.equal(formatIntervalLabel(15), "Every 15 minutes");
  assert.equal(formatIntervalLabel(30), "Every 30 minutes");
  assert.equal(formatIntervalLabel(60), "Every 1 hour");
  assert.equal(formatIntervalLabel(360), "Every 6 hours");
  assert.equal(formatIntervalLabel(1440), "Once a day");
  assert.equal(formatIntervalLabel(120), "Every 120 minutes");
});

test("ingress.service: formatPresetIntervalLabel formats presets", () => {
  assert.equal(formatPresetIntervalLabel(15), "15 minutes");
  assert.equal(formatPresetIntervalLabel(30), "30 minutes");
  assert.equal(formatPresetIntervalLabel(60), "1 hour");
  assert.equal(formatPresetIntervalLabel(360), "6 hours");
  assert.equal(formatPresetIntervalLabel(1440), "1 day");
  assert.equal(formatPresetIntervalLabel(45), "45 minutes");
});

test("ingress.service: isValidInterval checks allowed set", () => {
  assert.equal(isValidInterval(15), true);
  assert.equal(isValidInterval(30), true);
  assert.equal(isValidInterval(60), true);
  assert.equal(isValidInterval(360), true);
  assert.equal(isValidInterval(1440), true);
  assert.equal(isValidInterval(45), false);
  assert.equal(isValidInterval(0), false);
});

test("ingress.service: getStatusColor maps status string to style token", () => {
  assert.equal(getStatusColor("running"), "running");
  assert.equal(getStatusColor("error"), "error");
  assert.equal(getStatusColor("failed"), "error");
  assert.equal(getStatusColor("idle"), "idle");
  assert.equal(getStatusColor("disabled"), "disabled");
});

test("ingress.service: getEmailConnectionStatus handles null and unconfigured state", () => {
  const result = getEmailConnectionStatus(null);
  assert.equal(result.state, "not_set_up");
  assert.equal(result.label, "Not set up");
  assert.equal(result.badgeClass, "badge-dark");
  assert.equal(result.message, "Email access is configured on the server for now.");

  const unconfiguredConfig: IngressConfig = {
    id: "cfg-1",
    householdId: "hh-1",
    userId: "u-1",
    provider: "gmail",
    isEnabled: true,
    intervalMinutes: 60,
    lastRunAt: null,
    nextRunAt: null,
    status: "idle",
    lastError: null,
    createdAt: null,
  };
  const unconfiguredResult = getEmailConnectionStatus(unconfiguredConfig);
  assert.equal(unconfiguredResult.state, "not_set_up");
  assert.equal(unconfiguredResult.label, "Not set up");
});

test("ingress.service: getEmailConnectionStatus detects connected state", () => {
  const activeStatus: IngressStatus = {
    householdId: "hh-1",
    provider: "gmail",
    status: "idle",
    isEnabled: true,
    intervalMinutes: 60,
    lastRunAt: "2025-05-10T12:00:00Z",
    nextRunAt: "2025-05-10T13:00:00Z",
    lastError: null,
    totalProcessed: 5,
    lastHistoryId: "12345",
    lastEmailInternalDate: 1715342400000,
    checkpointUpdatedAt: "2025-05-10T12:00:00Z",
  };
  const result = getEmailConnectionStatus(activeStatus);
  assert.equal(result.state, "connected");
  assert.equal(result.label, "Connected");
  assert.equal(result.badgeClass, "badge-success");
});

test("ingress.service: getEmailConnectionStatus handles errors without exposing paths or secrets", () => {
  const errorStatus: IngressStatus = {
    householdId: "hh-1",
    provider: "gmail",
    status: "error",
    isEnabled: true,
    intervalMinutes: 60,
    lastRunAt: "2025-05-10T12:00:00Z",
    nextRunAt: null,
    lastError: "File /var/run/secrets/token.json: Permission denied in line 42",
    totalProcessed: 0,
    lastHistoryId: null,
    lastEmailInternalDate: null,
    checkpointUpdatedAt: null,
  };
  const result = getEmailConnectionStatus(errorStatus);
  assert.equal(result.state, "error");
  assert.equal(result.label, "Needs attention");
  assert.equal(result.badgeClass, "badge-danger");
  assert.equal(result.message.includes("/var/run/secrets"), false);
  assert.equal(result.message.includes("token.json"), false);
  assert.equal(result.message, "Failed to complete email check. Please try again later.");
});

test("ingress.service: getExecutionStatusBadge maps status strings accurately", () => {
  assert.deepEqual(getExecutionStatusBadge("running"), {
    label: "Checking now...",
    badgeClass: "badge-info",
  });
  assert.deepEqual(getExecutionStatusBadge("error"), {
    label: "Needs attention",
    badgeClass: "badge-danger",
  });
  assert.deepEqual(getExecutionStatusBadge("failed"), {
    label: "Needs attention",
    badgeClass: "badge-danger",
  });
  assert.deepEqual(getExecutionStatusBadge("idle"), {
    label: "Waiting",
    badgeClass: "badge-dark",
  });
  assert.deepEqual(getExecutionStatusBadge(null), {
    label: "Waiting",
    badgeClass: "badge-dark",
  });
});

test("ingress.service: formatFriendlyDateTime formats ISO dates accurately with UTC timeZone", () => {
  assert.equal(formatFriendlyDateTime(null), "Never");
  assert.equal(formatFriendlyDateTime(undefined), "Never");
  assert.equal(formatFriendlyDateTime("invalid-date"), "Never");

  const formatted = formatFriendlyDateTime("2026-05-10T14:30:00.000Z");
  assert.equal(formatted, "May 10, 2:30 PM UTC");
});

test("ingress.service: formatFriendlyNextRun handles paused and scheduled runs", () => {
  assert.equal(formatFriendlyNextRun("2026-05-10T14:30:00.000Z", false), "Paused");
  assert.equal(formatFriendlyNextRun(null, true), "Not scheduled");
  assert.equal(
    formatFriendlyNextRun("2026-05-10T14:30:00.000Z", true),
    "May 10, 2:30 PM UTC"
  );
});

test("ingress.service: sanitizeErrorMessage scrubs sensitive internals and handles error types", () => {
  // Stack traces & python error lines
  assert.equal(
    sanitizeErrorMessage("Traceback (most recent call last):\n  File 'main.py', line 12"),
    "Failed to complete email check. Please try again later."
  );

  // File paths & system paths
  assert.equal(
    sanitizeErrorMessage("Failed reading /etc/ssl/certs/key.pem: not found"),
    "Failed to complete email check. Please try again later."
  );

  // Database / SQL keywords & details
  assert.equal(
    sanitizeErrorMessage("SELECT * FROM ingress_configs WHERE user_id = '123' failed"),
    "Failed to complete email check. Please try again later."
  );
  assert.equal(
    sanitizeErrorMessage("psycopg.errors.UniqueViolation: duplicate key value violates unique constraint"),
    "Failed to complete email check. Please try again later."
  );

  // URLs with credentials
  assert.equal(
    sanitizeErrorMessage("Failed connecting to https://user:secret123@db.example.com/sync"),
    "Failed to complete email check. Please try again later."
  );

  // API keys / tokens
  assert.equal(
    sanitizeErrorMessage("Failed with key sk-1234567890abcdef1234567890"),
    "Failed to complete email check. Please try again later."
  );

  // 401 / Unauthorized
  assert.equal(
    sanitizeErrorMessage("HTTP 401 Unauthorized: Token verification failed"),
    "We could not load your email settings. Please sign in again."
  );

  // Network failures
  assert.equal(
    sanitizeErrorMessage("Failed to fetch"),
    "Unable to reach the server. Please check your connection."
  );

  // Timeouts
  assert.equal(
    sanitizeErrorMessage("Gateway timed out"),
    "Connection timed out while checking email. Please try again."
  );

  // Short clean error
  assert.equal(
    sanitizeErrorMessage("Mailbox is temporarily full"),
    "Mailbox is temporarily full"
  );
});
