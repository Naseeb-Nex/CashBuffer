import { getKindeServerSession } from "@kinde-oss/kinde-auth-nextjs/server";
import { syncKindeUser, type SyncedUser } from "./syncUser.ts";

export interface AuthenticatedSession {
  isAuthenticated: boolean;
  kindeUser: {
    id: string;
    email: string | null;
    given_name: string | null;
    family_name: string | null;
    picture: string | null;
  } | null;
  dbUser: SyncedUser | null;
}

/**
 * Server session helper: checks Kinde authentication,
 * retrieves Kinde user, and synchronizes with Neon DB users table.
 */
export async function getAuthenticatedUser(): Promise<AuthenticatedSession> {
  try {
    const { isAuthenticated, getUser } = getKindeServerSession();
    const authed = await isAuthenticated();
    if (!authed) {
      return { isAuthenticated: false, kindeUser: null, dbUser: null };
    }

    const kindeUser = await getUser();
    if (!kindeUser || !kindeUser.id) {
      return { isAuthenticated: false, kindeUser: null, dbUser: null };
    }

    const dbUser = await syncKindeUser(kindeUser);
    return {
      isAuthenticated: true,
      kindeUser,
      dbUser,
    };
  } catch (err) {
    console.error("Error retrieving authenticated session:", err);
    return { isAuthenticated: false, kindeUser: null, dbUser: null };
  }
}
