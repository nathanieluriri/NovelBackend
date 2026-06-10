import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type ReadingProgressDoc = Record<string, any>;

const ReadingProgressSchema = new Schema<ReadingProgressDoc>(
  {
    userId: { type: String, required: true }, // unique — 1 doc per user
    chapterId: { type: String, required: true },
    pageId: { type: String, required: true },
    dateCreated: { type: String }, // $setOnInsert only
    dateUpdated: { type: String }, // every upsert
  },
  { collection: "reading_progress", versionKey: false, strict: true, autoIndex: false },
);

ReadingProgressSchema.index({ userId: 1 }, { unique: true });

export const ReadingProgress: Model<ReadingProgressDoc> =
  (models.ReadingProgress as Model<ReadingProgressDoc>) ??
  model<ReadingProgressDoc>("ReadingProgress", ReadingProgressSchema);
