import test from "node:test";
import assert from "node:assert/strict";
import { syncKindeUser } from "./syncUser.ts";
import { getDb } from "../db/neon.ts";

test("syncKindeUser: inserts new user and updates existing on email change", async () => {
  if (!process.env.DATABASE_URL) {
    // Skip if running in an environment without database connection
    return;
  }

  const testIdpUserId = `test_kinde_user_${Date.now()}`;
  const initialEmail = `${testIdpUserId}@cashbuffer.local`;
  const updatedEmail = `${testIdpUserId}_updated@cashbuffer.local`;

  const sql = getDb();

  try {
    // 1. Initial sync (insert)
    const user1 = await syncKindeUser({
      id: testIdpUserId,
      email: initialEmail,
    });

    assert.ok(user1.id, "User ID UUID must be present");
    assert.equal(user1.idp_user_id, testIdpUserId);
    assert.equal(user1.email, initialEmail);

    // 2. Repeat sync with same email (idempotency)
    const user2 = await syncKindeUser({
      id: testIdpUserId,
      email: initialEmail,
    });
    assert.equal(user2.id, user1.id);
    assert.equal(user2.email, initialEmail);

    // 3. Sync with updated email
    const user3 = await syncKindeUser({
      id: testIdpUserId,
      email: updatedEmail,
    });
    assert.equal(user3.id, user1.id);
    assert.equal(user3.email, updatedEmail);
  } finally {
    // Clean up test user
    await sql`DELETE FROM users WHERE idp_user_id = ${testIdpUserId}`;
  }
});
