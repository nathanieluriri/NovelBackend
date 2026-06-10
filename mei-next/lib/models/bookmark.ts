import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type BookmarkDoc = Record<string, any>;

const BookmarkSchema = new Schema<BookmarkDoc>(
  {
    userId: { type: String, required: true },
    targetType: { type: String, enum: ["book", "chapter", "page"], required: true },
    targetId: { type: String, required: true },
    chapterLabel: { type: String, default: null },
    chapterId: { type: String, default: null },
    pageId: { type: String, default: null }, // legacy
    dateCreated: { type: String },
  },
  { collection: "bookmarks", versionKey: false, strict: true, autoIndex: false },
);

BookmarkSchema.index(
  { userId: 1, targetType: 1, targetId: 1 },
  {
    unique: true,
    partialFilterExpression: { targetType: { $exists: true }, targetId: { $exists: true } },
  },
);
BookmarkSchema.index({ userId: 1, dateCreated: -1 });

export const Bookmark: Model<BookmarkDoc> =
  (models.Bookmark as Model<BookmarkDoc>) ?? model<BookmarkDoc>("Bookmark", BookmarkSchema);
