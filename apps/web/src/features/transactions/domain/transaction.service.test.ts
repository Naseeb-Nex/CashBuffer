import test from "node:test";
import assert from "node:assert/strict";
import {
  computeNetBuffer,
  formatCurrency,
  formatDate,
  getStatusBadgeVariant,
  isQuarantined,
  validateTransactionInput,
} from "./transaction.service.ts";

test("transaction.service: computeNetBuffer calculates correctly", () => {
  assert.equal(computeNetBuffer(1000, 450.5), 549.5);
  assert.equal(computeNetBuffer(200, 500), -300);
});

test("transaction.service: formatCurrency formats standard numbers", () => {
  const formatted = formatCurrency(1500, "INR");
  assert.ok(formatted.includes("1,500") || formatted.includes("1500"));
});

test("transaction.service: formatDate handles valid and invalid strings", () => {
  assert.equal(formatDate(""), "N/A");
  assert.ok(formatDate("2026-11-17").includes("2026"));
});

test("transaction.service: isQuarantined correctly detects status", () => {
  assert.equal(isQuarantined({ status: "needs_review" }), true);
  assert.equal(isQuarantined({ status: "parsed" }), true);
  assert.equal(isQuarantined({ status: "categorized" }), false);
});

test("transaction.service: validateTransactionInput checks positive amount and vendor", () => {
  assert.equal(validateTransactionInput(0, "Vendor"), "Amount must be a positive number");
  assert.equal(validateTransactionInput(-5, "Vendor"), "Amount must be a positive number");
  assert.equal(validateTransactionInput(10, ""), "Vendor/Description is required");
  assert.equal(validateTransactionInput(10, "   "), "Vendor/Description is required");
  assert.equal(validateTransactionInput(10, "Swiggy"), null);
});

test("transaction.service: getStatusBadgeVariant returns correct theme tokens", () => {
  assert.equal(getStatusBadgeVariant("categorized"), "success");
  assert.equal(getStatusBadgeVariant("needs_review"), "warning");
  assert.equal(getStatusBadgeVariant("parsed"), "info");
});
