import { getKindeServerSession } from "@kinde-oss/kinde-auth-nextjs/server";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { isAuthenticated, getAccessTokenRaw } = getKindeServerSession();
    const authed = await isAuthenticated();
    if (!authed) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = await getAccessTokenRaw();
    if (!token) {
      return NextResponse.json({ error: "No access token" }, { status: 401 });
    }

    return NextResponse.json({ accessToken: token });
  } catch (err: unknown) {
    console.error("Error retrieving access token:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
