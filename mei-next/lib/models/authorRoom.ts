import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type AuthorRoomDoc = Record<string, any>;

const AuthorRoomSchema = new Schema<AuthorRoomDoc>(
  {
    text: { type: String, required: true },
    chapterId: { type: String, required: true },
    // Epoch seconds in storage; ISO-fied at the serializer layer.
    date_created: { type: Number, default: () => Math.floor(Date.now() / 1000) },
    last_updated: { type: Number, default: () => Math.floor(Date.now() / 1000) },
  },
  { collection: "author_rooms", versionKey: false, strict: true, autoIndex: false },
);

export const AuthorRoom: Model<AuthorRoomDoc> =
  (models.AuthorRoom as Model<AuthorRoomDoc>) ?? model<AuthorRoomDoc>("AuthorRoom", AuthorRoomSchema);
