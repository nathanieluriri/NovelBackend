import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type AdminDoc = Record<string, any>;

const AdminSchema = new Schema<AdminDoc>(
  {
    email: { type: String, required: true },
    password: { type: String, required: true }, // bcrypt
    firstName: { type: String, default: null },
    lastName: { type: String, default: null },
    avatar: { type: String, default: null },
    invitedBy: { type: String, default: null },
    provider: { type: String, default: null }, // present in delete query
    authProviders: { type: [String], default: [] },
    dateCreated: { type: String },
  },
  { collection: "admins", versionKey: false, strict: true, autoIndex: false },
);

export const Admin: Model<AdminDoc> =
  (models.Admin as Model<AdminDoc>) ?? model<AdminDoc>("Admin", AdminSchema);
