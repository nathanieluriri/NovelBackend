import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type LoginAttemptDoc = Record<string, any>;

const LoginAttemptSchema = new Schema<LoginAttemptDoc>(
  {
    ip: { type: String, required: true },
    city: { type: String, default: null },
    region: { type: String, default: null },
    country: { type: String, default: null },
    latitude: { type: String, default: null },
    longitude: { type: String, default: null },
    Network: { type: String, default: null }, // ⚠ capital N — legacy field name
    timezone: { type: String, default: null },
    dateTime: { type: String, required: true },
    clientType: { type: String, required: true },
    userId: { type: String, required: true },
  },
  { collection: "LoginAttempts", versionKey: false, strict: true, autoIndex: false },
);

export const LoginAttempt: Model<LoginAttemptDoc> =
  (models.LoginAttempt as Model<LoginAttemptDoc>) ??
  model<LoginAttemptDoc>("LoginAttempt", LoginAttemptSchema);
