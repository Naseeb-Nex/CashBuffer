import { NextResponse } from "next/server";
import { getAuthenticatedUser } from "@/shared/infrastructure/auth/session.ts";

export const dynamic = "force-dynamic";

export async function GET() {
  const session = await getAuthenticatedUser();
  if (!session.isAuthenticated || !session.dbUser) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  return NextResponse.json({
    status: "synchronized",
    user: session.dbUser,
  });
}
