import test from "node:test";
import assert from "node:assert/strict";
import { createMessage, formatTime, fromAssistantResponse } from "./chat.service.ts";

test("chat.service: createMessage initializes user and assistant messages with unique ID and timestamp", () => {
  const msg = createMessage("user", "Hello CashBuffer");
  assert.equal(msg.sender, "user");
  assert.equal(msg.text, "Hello CashBuffer");
  assert.ok(msg.id.startsWith("msg-"));
  assert.ok(msg.timestamp.length > 0);
});

test("chat.service: fromAssistantResponse handles actions and widgets", () => {
  const res = {
    reply: "Here is your summary.",
    actionsExecuted: ["query_balance"],
    widgets: [{ type: "kpi", data: { total: 500 } }],
    context: {},
  };

  const msg = fromAssistantResponse(res);
  assert.equal(msg.sender, "assistant");
  assert.equal(msg.text, "Here is your summary.");
  assert.deepEqual(msg.actionsExecuted, ["query_balance"]);
  assert.equal(msg.widgets?.length, 1);
});

test("chat.service: formatTime formats valid iso timestamps", () => {
  const time = formatTime("2026-11-17T12:30:00Z");
  assert.ok(typeof time === "string" && time.length > 0);
  assert.equal(formatTime("invalid"), "");
});
