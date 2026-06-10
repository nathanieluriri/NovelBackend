import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type EntitlementDoc = Record<string, any>;

const EntitlementSchema = new Schema<EntitlementDoc>(
  {
    userId: { type: String, required: true },
    chapterId: { type: String, required: true },
    grantType: { type: String, enum: ["chapter_unlock"], default: "chapter_unlock" },
    source: { type: String, default: null }, // "stars_wallet" | "cash_checkout"
    txRef: { type: String, default: null },
    createdAt: { type: String },
  },
  { collection: "entitlements", versionKey: false, strict: true, autoIndex: false },
);

EntitlementSchema.index({ userId: 1, chapterId: 1 }, { unique: true });

export const Entitlement: Model<EntitlementDoc> =
  (models.Entitlement as Model<EntitlementDoc>) ??
  model<EntitlementDoc>("Entitlement", EntitlementSchema);
