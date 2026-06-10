import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type ReactionDoc = Record<string, any>;

const ReactionSchema = new Schema<ReactionDoc>(
  {
    reaction: { type: String, required: true },
    authorRoomId: { type: String, required: true },
    userId: { type: String, required: true },
    // Epoch seconds in storage; serialized to ISO `dateCreated`/`lastUpdated` on the wire.
    date_created: { type: Number, default: () => Math.floor(Date.now() / 1000) },
    last_updated: { type: Number, default: () => Math.floor(Date.now() / 1000) },
  },
  { collection: "reactions", versionKey: false, strict: true, autoIndex: false },
);

ReactionSchema.index({ userId: 1, authorRoomId: 1 }, { unique: true });

export const Reaction: Model<ReactionDoc> =
  (models.Reaction as Model<ReactionDoc>) ?? model<ReactionDoc>("Reaction", ReactionSchema);
