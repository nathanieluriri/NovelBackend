/**
 * READ-ONLY diagnostic for the reaction overwrite (409) bug.
 * Inspects indexes + stored field BSON types on the `reactions` collection.
 * Performs NO writes. Run: npx tsx scripts/diagnose-reactions.ts
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import mongoose from "mongoose";
import { db } from "../lib/db";

function loadEnvFiles(): void {
  for (const name of [".env.local", ".env"]) {
    const p = resolve(process.cwd(), name);
    if (!existsSync(p)) continue;
    for (const line of readFileSync(p, "utf8").split(/\r?\n/)) {
      const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
      if (!m) continue;
      let v = m[2];
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
      if (process.env[m[1]] === undefined) process.env[m[1]] = v;
    }
  }
}

function bsonType(v: unknown): string {
  if (v === null) return "null";
  if (v === undefined) return "undefined";
  if (v instanceof mongoose.Types.ObjectId) return "ObjectId";
  return typeof v;
}

async function main(): Promise<void> {
  loadEnvFiles();
  const conn = await db();
  const coll = conn.connection.collection("reactions");

  console.log("=== INDEXES on 'reactions' ===");
  const indexes = await coll.indexes();
  for (const ix of indexes) {
    console.log(JSON.stringify({ name: ix.name, key: ix.key, unique: ix.unique ?? false, collation: ix.collation?.locale ?? null }));
  }

  const total = await coll.countDocuments({});
  console.log(`\n=== total reactions: ${total} ===`);

  console.log("\n=== field BSON types (sample up to 10 docs) ===");
  const docs = await coll.find({}).limit(10).toArray();
  for (const d of docs) {
    console.log(
      `userId=${bsonType(d.userId)} authorRoomId=${bsonType(d.authorRoomId)} reaction=${bsonType(d.reaction)} _id=${bsonType(d._id)}`,
    );
  }

  // Count how many docs store userId / authorRoomId as ObjectId vs string.
  const asObjId = await coll.countDocuments({ userId: { $type: "objectId" } });
  const roomAsObjId = await coll.countDocuments({ authorRoomId: { $type: "objectId" } });
  const userAsStr = await coll.countDocuments({ userId: { $type: "string" } });
  const roomAsStr = await coll.countDocuments({ authorRoomId: { $type: "string" } });
  console.log(`\n=== type breakdown ===`);
  console.log(`userId:       string=${userAsStr}  objectId=${asObjId}`);
  console.log(`authorRoomId: string=${roomAsStr}  objectId=${roomAsObjId}`);

  await mongoose.disconnect();
  console.log("\n[diagnose-reactions] done (read-only, no writes)");
}

main().catch((err) => {
  console.error("[diagnose-reactions] fatal:", err);
  process.exit(1);
});
