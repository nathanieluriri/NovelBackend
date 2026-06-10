import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type ChapterDoc = Record<string, any>;

const ChapterSchema = new Schema<ChapterDoc>(
  {
    bookId: { type: String, required: true },
    chapterLabel: { type: String, default: null },
    status: { type: String, default: null }, // legacy
    accessType: { type: String, enum: ["free", "subscription", "paid"], default: "free" },
    unlockBundleId: { type: String, default: null }, // required iff accessType === "paid"
    coverImage: { type: String, default: null },
    number: { type: Number, default: 0 },
    dateCreated: { type: String },
    dateUpdated: { type: String },
    pageCount: { type: Number, default: 0 },
    pages: { type: [String], default: null },
  },
  { collection: "chapters", versionKey: false, strict: true, autoIndex: false },
);

ChapterSchema.index({ bookId: 1, number: 1 });

export const Chapter: Model<ChapterDoc> =
  (models.Chapter as Model<ChapterDoc>) ?? model<ChapterDoc>("Chapter", ChapterSchema);
