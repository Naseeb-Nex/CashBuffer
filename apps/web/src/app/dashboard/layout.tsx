import { getAuthenticatedUser } from "@/shared/infrastructure/auth/session.ts";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Synchronize authenticated user with Neon DB on access
  await getAuthenticatedUser();
  return <>{children}</>;
}
