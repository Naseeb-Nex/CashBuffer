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
  assert.equal(formatIntervalLabel(60), "Every 1 hour");
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
});

test("ingress.service: getEmailConnectionStatus handles null and unconfigured state", () => {
  const result = getEmailConnectionStatus(null);
  assert.equal(result.state, "not_set_up");
  assert.equal(result.label, "Not set up");
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
  assert.equal(result.message.includes("/var/run/secrets"), false);
  assert.equal(result.message.includes("token.json"), false);
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

test("ingress.service: formatFriendlyDateTime formats ISO dates or returns Never", () => {
  assert.equal(formatFriendlyDateTime(null), "Never");
  assert.equal(formatFriendlyDateTime(undefined), "Never");
  assert.equal(formatFriendlyDateTime("invalid-date"), "Never");
  const formatted = formatFriendlyDateTime("2025-05-10T14:30:00Z");
  assert.ok(formatted.length > 3);
});

test("ingress.service: formatFriendlyNextRun handles paused and scheduled runs", () => {
  assert.equal(formatFriendlyNextRun("2025-05-10T14:30:00Z", false), "Paused");
  assert.equal(formatFriendlyNextRun(null, true), "Not scheduled");
  const formatted = formatFriendlyNextRun("2025-05-10T14:30:00Z", true);
  assert.ok(formatted !== "Paused" && formatted !== "Not scheduled");
});

test("ingress.service: sanitizeErrorMessage scrubs sensitive internals", () => {
  assert.equal(
    sanitizeErrorMessage("Connection refused to /etc/credentials/key.pem"),
    "Failed to complete email check. Please try again later."
  );
  assert.equal(
    sanitizeErrorMessage("Failed to fetch"),
    "Unable to reach the server. Please check your connection."
  );
  assert.equal(
    sanitizeErrorMessage("401 Unauthorized token expired"),
    "Authentication failed. Please check server configuration."
  );
  assert.equal(
    sanitizeErrorMessage("Daemon is temporarily unavailable"),
    "Daemon is temporarily unavailable"
  );
});
