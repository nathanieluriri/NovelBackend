import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type GoogleOAuthExchangeDoc = Record<string, any>;

const GoogleOAuthExchangeSchema = new Schema<GoogleOAuthExchangeDoc>(
  {
    codeHash: { type: String, required: true }, // sha256(code)
    userId: { type: String, required: true },
    targetAlias: { type: String, required: true }, // local|dev|staging|prod
    createdAt: { type: Date, default: () => new Date() },
    expiresAt: { type: Date, required: true }, // TTL
    consumedAt: { type: Date, default: null }, // single-use
  },
  { collection: "google_oauth_exchanges", versionKey: false, strict: true, autoIndex: false },
);

GoogleOAuthExchangeSchema.index({ codeHash: 1 }, { unique: true });
GoogleOAuthExchangeSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

export const GoogleOAuthExchange: Model<GoogleOAuthExchangeDoc> =
  (models.GoogleOAuthExchange as Model<GoogleOAuthExchangeDoc>) ??
  model<GoogleOAuthExchangeDoc>("GoogleOAuthExchange", GoogleOAuthExchangeSchema);
