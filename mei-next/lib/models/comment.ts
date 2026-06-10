import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type CommentDoc = Record<string, any>;

const CommentSchema = new Schema<CommentDoc>(
  {
    userId: { type: String, required: true },
    role: { type: String, required: true },
    text: { type: String, required: true },
    targetType: { type: String, enum: ["book", "chapter", "page"], required: true },
    targetId: { type: String, required: true },
    parentCommentId: { type: String, default: null }, // self-referential (threaded replies)
    commentType: {
      type: String,
      enum: ["reply_target", "Reply To Chapter", "Reply To Comment", "Reply To Reply"],
      default: "reply_target",
    },
    chapterId: { type: String, default: null }, // legacy chapter-only comments
    dateCreated: { type: String },
  },
  { collection: "comments", versionKey: false, strict: true, autoIndex: false },
);

CommentSchema.index({ targetType: 1, targetId: 1, dateCreated: -1 });
CommentSchema.index({ userId: 1, dateCreated: -1 });

export const Comment: Model<CommentDoc> =
  (models.Comment as Model<CommentDoc>) ?? model<CommentDoc>("Comment", CommentSchema);
