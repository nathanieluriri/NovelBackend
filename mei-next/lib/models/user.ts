import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type UserDoc = Record<string, any>;

const SubscriptionInfoSchema = new Schema(
  {
    active: { type: Boolean, default: false },
    expiresAt: { type: String, default: null },
  },
  { _id: false },
);

const UserSchema = new Schema<UserDoc>(
  {
    provider: { type: String, enum: ["credentials", "google"], required: true },
    email: { type: String, required: true },
    password: { type: String, default: null }, // bcrypt; null for google
    googleAccessToken: { type: String, default: null },
    firstName: { type: String, default: null },
    lastName: { type: String, default: null },
    avatar: { type: String, default: null },
    status: { type: String, enum: ["Active", "Inactive", "Suspended"], default: "Active" },
    balance: { type: Number, default: 0 }, // stars wallet
    unlockedChapters: { type: [String], default: [] }, // legacy chapter ids
    authProviders: { type: [String], default: [] }, // lowercased, deduped
    subscription: { type: SubscriptionInfoSchema, default: () => ({}) },
    dateCreated: { type: String }, // ISO on create
  },
  { collection: "users", versionKey: false, strict: true, autoIndex: false },
);

export const User: Model<UserDoc> =
  (models.User as Model<UserDoc>) ?? model<UserDoc>("User", UserSchema);
