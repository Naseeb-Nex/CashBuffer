import { withAuth } from "@kinde-oss/kinde-auth-nextjs/middleware";
import type { NextRequest } from "next/server";

export default function middleware(req: NextRequest) {
  return withAuth(req);
}

export const config = {
  matcher: [
    "/dashboard",
    "/dashboard/:path*",
    "/quarantine",
    "/quarantine/:path*",
    "/ingress",
    "/ingress/:path*",
    "/settings",
    "/settings/:path*",
    "/chat",
    "/chat/:path*",
  ],
};
