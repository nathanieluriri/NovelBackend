import { Schema, model, models, type Model } from "mongoose";

/**
 * Loose doc type at the seam — legacy data is heterogeneous.
 * NB: some old docs carry a snake `chapter_id` key (used in one legacy delete
 * query) — handle both keys when deleting pages by chapter (service layer).
 */
export type PageDoc = Record<string, any>;

const PageSchema = new Schema<PageDoc>(
  {
    chapterId: { type: String, required: true },
    textContent: { type: String, required: true }, // HTML
    status: { type: String, required: true },
    number: { type: Number, default: 0 }, // exists in DB though not in legacy Pydantic
    textCount: { type: Number, default: 0 }, // word count of cleaned HTML
    dateCreated: { type: String },
    dateUpdated: { type: String },
  },
  { collection: "pages", versionKey: false, strict: true, autoIndex: false },
);

PageSchema.index({ chapterId: 1, number: 1 });

export const Page: Model<PageDoc> =
  (models.Page as Model<PageDoc>) ?? model<PageDoc>("Page", PageSchema);
