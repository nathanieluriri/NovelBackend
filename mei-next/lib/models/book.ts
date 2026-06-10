import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type BookDoc = Record<string, any>;

const BookSchema = new Schema<BookDoc>(
  {
    name: { type: String, required: true },
    number: { type: Number, required: true },
    dateCreated: { type: String },
    dateUpdated: { type: String },
    chapterCount: { type: Number, default: 0 },
    chapters: { type: [String], default: null }, // chapter id strings
  },
  { collection: "books", versionKey: false, strict: true, autoIndex: false },
);

export const Book: Model<BookDoc> =
  (models.Book as Model<BookDoc>) ?? model<BookDoc>("Book", BookSchema);
