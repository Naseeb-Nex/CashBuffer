import test from "node:test";
import assert from "node:assert/strict";
import type { Transaction } from "../../transactions/domain/transaction.model.ts";
import { filterNeedsReview, sortQuarantineByDate } from "./quarantine.service.ts";

test("quarantine.service: filterNeedsReview keeps only unreviewed or parsed transactions", () => {
  const transactions: Transaction[] = [
    {
      id: 1,
      userId: "u1",
      amount: 100,
      currency: "INR",
      isInflow: false,
      recordDate: "2026-11-17",
      vendorRaw: "Vendor 1",
      categoryId: null,
      status: "needs_review",
    },
    {
      id: 2,
      userId: "u1",
      amount: 200,
      currency: "INR",
      isInflow: false,
      recordDate: "2026-11-16",
      vendorRaw: "Vendor 2",
      categoryId: 1,
      status: "categorized",
    },
    {
      id: 3,
      userId: "u1",
      amount: 300,
      currency: "INR",
      isInflow: false,
      recordDate: "2026-11-15",
      vendorRaw: "Vendor 3",
      categoryId: null,
      status: "parsed",
    },
  ];

  const filtered = filterNeedsReview(transactions);
  assert.equal(filtered.length, 2);
  assert.equal(filtered[0].id, 1);
  assert.equal(filtered[1].id, 3);
});

test("quarantine.service: sortQuarantineByDate sorts newest first", () => {
  const txList: Transaction[] = [
    {
      id: 1,
      userId: "u1",
      amount: 50,
      currency: "INR",
      isInflow: false,
      recordDate: "2026-11-10",
      vendorRaw: "Old",
      categoryId: null,
      status: "needs_review",
    },
    {
      id: 2,
      userId: "u1",
      amount: 100,
      currency: "INR",
      isInflow: false,
      recordDate: "2026-11-17",
      vendorRaw: "New",
      categoryId: null,
      status: "needs_review",
    },
  ];

  const sorted = sortQuarantineByDate(txList);
  assert.equal(sorted[0].id, 2);
  assert.equal(sorted[1].id, 1);
});
