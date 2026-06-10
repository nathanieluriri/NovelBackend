import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type LikeDoc = Record<string, any>;

const LikeSchema = new Schema<LikeDoc>(
  {
    chapterId: { type: String, required: true },
    userId: { type: String, required: true },
    role: { type: String, required: true },
    likeType: {
      type: String,
      enum: ["Liked Chapter", "Liked Comment", "Liked Comment Reply", "Liked Reply To Reply"],
      default: "Liked Chapter",
    },
    // ⚠ MISSPELLED on purpose — sacred wire/storage quirk (schema.md §0).
    chapaterLabel: { type: String, required: true },
    dateCreated: { type: String },
  },
  { collection: "likes", versionKey: false, strict: true, autoIndex: false },
);

LikeSchema.index({ userId: 1, chapterId: 1 }, { unique: true });
LikeSchema.index({ chapterId: 1 });

export const Like: Model<LikeDoc> =
  (models.Like as Model<LikeDoc>) ?? model<LikeDoc>("Like", LikeSchema);
