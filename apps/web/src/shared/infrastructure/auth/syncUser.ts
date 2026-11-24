import { getDb } from "../db/neon.ts";

export interface SyncedUser {
  id: string;
  idp_user_id: string;
  email: string | null;
  telegram_chat_id: string | null;
  created_at: string | Date;
  updated_at: string | Date;
}

export interface KindeUserPayload {
  id: string;
  email?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  picture?: string | null;
}

/**
 * Synchronizes a Kinde authenticated user with Neon DB `users` table.
 * Checks by idp_user_id and inserts/updates record if missing.
 */
export async function syncKindeUser(user: KindeUserPayload): Promise<SyncedUser> {
  if (!user || !user.id) {
    throw new Error("Invalid user payload: id (idp_user_id) is required");
  }

  const sql = getDb();
  const idpUserId = user.id.trim();
  const normalizedEmail = user.email ? user.email.trim().toLowerCase() : null;

  // 1. Check if user already exists by idp_user_id
  const existingByIdp = (await sql`
    SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at
    FROM users
    WHERE idp_user_id = ${idpUserId}
    LIMIT 1
  `) as SyncedUser[];

  if (existingByIdp.length > 0) {
    const existing = existingByIdp[0];
    if (normalizedEmail && existing.email !== normalizedEmail) {
      const updated = (await sql`
        UPDATE users
        SET email = ${normalizedEmail}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${existing.id}
        RETURNING id, idp_user_id, email, telegram_chat_id, created_at, updated_at
      `) as SyncedUser[];
      return updated[0];
    }
    return existing;
  }

  // 2. Fallback: check if existing user has this email to attach Kinde ID
  if (normalizedEmail) {
    const existingByEmail = (await sql`
      SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at
      FROM users
      WHERE email = ${normalizedEmail}
      LIMIT 1
    `) as SyncedUser[];

    if (existingByEmail.length > 0) {
      const updated = (await sql`
        UPDATE users
        SET idp_user_id = ${idpUserId}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${existingByEmail[0].id}
        RETURNING id, idp_user_id, email, telegram_chat_id, created_at, updated_at
      `) as SyncedUser[];
      return updated[0];
    }
  }

  // 3. User does not exist: insert new record
  const inserted = (await sql`
    INSERT INTO users (idp_user_id, email)
    VALUES (${idpUserId}, ${normalizedEmail})
    ON CONFLICT (idp_user_id) DO UPDATE
    SET email = EXCLUDED.email, updated_at = CURRENT_TIMESTAMP
    RETURNING id, idp_user_id, email, telegram_chat_id, created_at, updated_at
  `) as SyncedUser[];

  return inserted[0];
}
