import test from "node:test";
import assert from "node:assert/strict";
import {
  toBackendCreatePayload,
  toBackendUpdatePayload,
  toDomainCategory,
  toDomainFinancialSummary,
  toDomainTransaction,
} from "./transaction.mapper.ts";

test("transaction.mapper: maps backend transaction DTO to domain model", () => {
  const dto = {
    id: 42,
    user_id: "usr_123",
    amount: 999.5,
    currency: "INR",
    is_inflow: false,
    record_date: "2026-11-17",
    vendor_raw: "AMAZON RETAIL",
    category_id: 3,
    status: "categorized" as const,
  };

  const domain = toDomainTransaction(dto);
  assert.equal(domain.id, 42);
  assert.equal(domain.userId, "usr_123");
  assert.equal(domain.amount, 999.5);
  assert.equal(domain.isInflow, false);
  assert.equal(domain.vendorRaw, "AMAZON RETAIL");
  assert.equal(domain.categoryId, 3);
  assert.equal(domain.status, "categorized");
});

test("transaction.mapper: maps backend summary DTO to domain model", () => {
  const dto = {
    total_inflow: 50000,
    total_outflow: 20000,
    net_buffer: 30000,
    transaction_count: 10,
    uncategorized_count: 2,
    category_breakdown: [
      { category_id: 1, category_name: "Groceries", total_amount: 5000 },
    ],
    linked_accounts_count: 1,
  };

  const domain = toDomainFinancialSummary(dto);
  assert.equal(domain.totalInflow, 50000);
  assert.equal(domain.totalOutflow, 20000);
  assert.equal(domain.netBuffer, 30000);
  assert.equal(domain.categoryBreakdown.length, 1);
  assert.equal(domain.categoryBreakdown[0].categoryName, "Groceries");
});

test("transaction.mapper: maps category DTO to domain model", () => {
  const dto = { id: 7, user_id: "u1", name: "Utilities", parent_id: null };
  const domain = toDomainCategory(dto);
  assert.equal(domain.id, 7);
  assert.equal(domain.name, "Utilities");
});

test("transaction.mapper: converts update inputs to snake_case payload", () => {
  const payload = toBackendUpdatePayload({
    categoryId: 5,
    vendorRaw: "New Vendor",
  });
  assert.equal(payload.category_id, 5);
  assert.equal(payload.vendor_raw, "New Vendor");
  assert.equal(payload.status, undefined);
});

test("transaction.mapper: converts create inputs to snake_case payload", () => {
  const payload = toBackendCreatePayload({
    amount: 150,
    vendorRaw: "Uber",
    isInflow: false,
    recordDate: "2026-11-17",
  });
  assert.equal(payload.amount, 150);
  assert.equal(payload.vendor_raw, "Uber");
  assert.equal(payload.is_inflow, false);
  assert.equal(payload.record_date, "2026-11-17");
});
