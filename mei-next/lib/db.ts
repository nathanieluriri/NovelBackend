import mongoose from "mongoose";

/**
 * Serverless-safe Mongoose singleton (see ../nextjs-migration/data-models.md).
 * Cached on globalThis so warm Vercel invocations and dev hot-reloads reuse the
 * same connection instead of exhausting the Mongo pool.
 */
type Cached = { conn: typeof mongoose | null; promise: Promise<typeof mongoose> | null };

const g = globalThis as unknown as { _mongoose?: Cached };
const cached: Cached = g._mongoose ?? { conn: null, promise: null };
g._mongoose = cached;

export async function db(): Promise<typeof mongoose> {
  if (cached.conn) return cached.conn;
  if (!cached.promise) {
    const url = process.env.MONGO_URL;
    if (!url) throw new Error("MONGO_URL is not set");
    cached.promise = mongoose.connect(url, {
      dbName: process.env.DB_NAME,
      maxPoolSize: 10,
    });
  }
  cached.conn = await cached.promise;
  return cached.conn;
}
