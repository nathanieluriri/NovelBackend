import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type ReadRecordDoc = Record<string, any>;

const ReadRecordSchema = new Schema<ReadRecordDoc>(
  {
    userId: { type: String, required: true },
    chapterId: { type: String, required: true },
    hasRead: { type: Boolean, required: true },
    dateCreated: { type: String }, // $setOnInsert (ISO string)
    lastUpdated: { type: Date }, // BSON date via $currentDate
  },
  { collection: "read", versionKey: false, strict: true, autoIndex: false },
);

ReadRecordSchema.index({ userId: 1, chapterId: 1 }, { unique: true });

export const ReadRecord: Model<ReadRecordDoc> =
  (models.ReadRecord as Model<ReadRecordDoc>) ?? model<ReadRecordDoc>("ReadRecord", ReadRecordSchema);
