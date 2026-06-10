import { Schema, model, models, type Model } from "mongoose";

/**
 * Loose doc type at the seam — legacy data is heterogeneous.
 * The row `_id` IS the opaque refresh token.
 */
export type RefreshTokenDoc = Record<string, any>;

const RefreshTokenSchema = new Schema<RefreshTokenDoc>(
  {
    userId: { type: String, required: true },
    previousAccessToken: { type: String, required: true },
    dateCreated: { type: String },
  },
  { collection: "refreshToken", versionKey: false, strict: true, autoIndex: false },
);

RefreshTokenSchema.index({ userId: 1 });

export const RefreshToken: Model<RefreshTokenDoc> =
  (models.RefreshToken as Model<RefreshTokenDoc>) ??
  model<RefreshTokenDoc>("RefreshToken", RefreshTokenSchema);
