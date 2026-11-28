import { getKindeServerSession } from "@kinde-oss/kinde-auth-nextjs/server";
import { type NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  // Disallow cross-origin requests
  const secFetchSite = req.headers.get("sec-fetch-site");
  if (secFetchSite && secFetchSite === "cross-site") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (origin && host) {
    try {
      const originHost = new URL(origin).host;
      if (originHost !== host) {
        return NextResponse.json({ error: "Forbidden" }, { status: 403 });
      }
    } catch {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }
  }

  try {
    const { isAuthenticated, getAccessTokenRaw } = getKindeServerSession();
    const authed = await isAuthenticated();
    if (!authed) {
      return NextResponse.json(
        { error: "Unauthorized" },
        {
          status: 401,
          headers: {
            "Cache-Control": "no-store, no-cache, must-revalidate",
            Pragma: "no-cache",
          },
        }
      );
    }

    const token = await getAccessTokenRaw();
    if (!token) {
      return NextResponse.json(
        { error: "No access token" },
        {
          status: 401,
          headers: {
            "Cache-Control": "no-store, no-cache, must-revalidate",
            Pragma: "no-cache",
          },
        }
      );
    }

    return NextResponse.json(
      { accessToken: token },
      {
        status: 200,
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate",
          Pragma: "no-cache",
        },
      }
    );
  } catch (err: unknown) {
    console.error("Error retrieving access token:", err instanceof Error ? err.message : "internal error");
    return NextResponse.json(
      { error: "Internal server error" },
      {
        status: 500,
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate",
          Pragma: "no-cache",
        },
      }
    );
  }
}

