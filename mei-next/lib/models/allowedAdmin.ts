import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type AllowedAdminDoc = Record<string, any>;

const AllowedAdminSchema = new Schema<AllowedAdminDoc>(
  {
    email: { type: String, required: true }, // unique
    invitedBy: { type: String, default: null },
    dateCreated: { type: String, default: null },
  },
  { collection: "AllowedAdmins", versionKey: false, strict: true, autoIndex: false },
);

AllowedAdminSchema.index({ email: 1 }, { unique: true });

export const AllowedAdmin: Model<AllowedAdminDoc> =
  (models.AllowedAdmin as Model<AllowedAdminDoc>) ??
  model<AllowedAdminDoc>("AllowedAdmin", AllowedAdminSchema);
