import { neon } from "@neondatabase/serverless";

let dbInstance: ReturnType<typeof neon> | null = null;

export function getDb() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL environment variable is not defined");
  }
  if (!dbInstance) {
    dbInstance = neon(connectionString);
  }
  return dbInstance;
}
