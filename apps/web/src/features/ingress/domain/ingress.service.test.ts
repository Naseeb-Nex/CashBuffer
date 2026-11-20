import test from "node:test";
import assert from "node:assert/strict";
import { formatIntervalLabel, getStatusColor, isValidInterval } from "./ingress.service.ts";

test("ingress.service: formatIntervalLabel formats standard intervals", () => {
  assert.equal(formatIntervalLabel(15), "Every 15 minutes");
  assert.equal(formatIntervalLabel(60), "Every 1 hour");
  assert.equal(formatIntervalLabel(1440), "Once a day (24h)");
  assert.equal(formatIntervalLabel(120), "Every 120 minutes");
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
