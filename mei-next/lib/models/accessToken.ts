import { Schema, model, models, type Model } from "mongoose";

/**
 * Loose doc type at the seam — legacy data is heterogeneous.
 * The row `_id` IS the opaque access token.
 */
export type AccessTokenDoc = Record<string, any>;

const AccessTokenSchema = new Schema<AccessTokenDoc>(
  {
    userId: { type: String, required: true },
    role: { type: String, default: "member" }, // "member" | "admin"
    status: { type: String, default: null }, // admin only: "inactive" | "active"
    dateCreated: { type: String }, // stale after 10 days
  },
  { collection: "accessToken", versionKey: false, strict: true, autoIndex: false },
);

AccessTokenSchema.index({ userId: 1 });

export const AccessToken: Model<AccessTokenDoc> =
  (models.AccessToken as Model<AccessTokenDoc>) ??
  model<AccessTokenDoc>("AccessToken", AccessTokenSchema);
