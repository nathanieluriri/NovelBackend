/**
 * Seed the default admin allow-list entry.
 *
 * Replicates the legacy FastAPI startup hook (api/v1/admin.py `startup_app` →
 * services/admin_services.setup_default_admin → repositories/admin_repo.create_default_admin):
 *   1. Read DEFAULT_ADMIN_EMAIL.
 *   2. If an AllowedAdmins doc with that email exists → no-op.
 *   3. Else insert { email, dateCreated: <ISO now> } and send the invitation
 *      email (firstName "Default", lastName "Admin" — best-effort, like legacy).
 *
 * Run: npx tsx scripts/seed-default-admin.ts
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import mongoose from "mongoose";
import { db } from "../lib/db";
import { AllowedAdmin } from "../lib/models";
import { sendAdminInvitation } from "../lib/email";
import { nowIso } from "../lib/util/dates";

/** Minimal .env loader (scripts run outside Next, which normally loads these). */
function loadEnvFiles(): void {
  for (const name of [".env.local", ".env"]) {
    const p = resolve(process.cwd(), name);
    if (!existsSync(p)) continue;
    for (const line of readFileSync(p, "utf8").split(/\r?\n/)) {
      const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
      if (!m) continue;
      let value = m[2];
      if (
        (value.startsWith('"') && value.endsWith('"') && value.length >= 2) ||
        (value.startsWith("'") && value.endsWith("'") && value.length >= 2)
      ) {
        value = value.slice(1, -1);
      }
      if (process.env[m[1]] === undefined) process.env[m[1]] = value;
    }
  }
}

async function main(): Promise<void> {
  loadEnvFiles();

  const email = process.env.DEFAULT_ADMIN_EMAIL;
  if (!email) {
    console.error("[seed-default-admin] DEFAULT_ADMIN_EMAIL is not set");
    process.exit(1);
  }

  await db();

  const existing = await AllowedAdmin.findOne({ email }).lean();
  if (existing) {
    console.log(`[seed-default-admin] "${email}" already in AllowedAdmins — nothing to do`);
  } else {
    await AllowedAdmin.create({ email, dateCreated: nowIso() });
    console.log(`[seed-default-admin] inserted "${email}" into AllowedAdmins`);
    console.log("sending invite");
    try {
      // Legacy: send_invitation(firstName="Default", lastName="Admin",
      //   invitedEmail=email, inviterEmail=EMAIL_USERNAME). Best-effort.
      await sendAdminInvitation({
        to: email,
        firstName: "Default",
        lastName: "Admin",
        inviterEmail: process.env.EMAIL_USERNAME ?? "",
      });
    } catch (err) {
      console.error("[seed-default-admin] invitation email failed (non-fatal):", err);
    }
  }

  console.log("Admin Setup complete");
  await mongoose.disconnect();
}

main().catch((err) => {
  console.error("[seed-default-admin] fatal:", err);
  process.exit(1);
});
