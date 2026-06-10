import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type TransactionDoc = Record<string, any>;

const TransactionSchema = new Schema<TransactionDoc>(
  {
    userId: { type: String, required: true },
    numberOfStars: { type: Number, default: null },
    // ⚠ PascalCase field name on purpose — sacred wire/storage quirk (schema.md §0).
    TransactionType: {
      type: String,
      required: true,
      enum: [
        "cash",
        "transferOfStarCurrencyBetweenAccounts",
        "transferOfStarCurrencyForChapterAccess",
        "subscriptionPurchase",
      ],
    },
    amount: { type: Number, default: null },
    paymentId: { type: String, required: true }, // dedup key (== txRef), application-level
    dateCreated: { type: String },
  },
  { collection: "transaction", versionKey: false, strict: true, autoIndex: false },
);

export const Transaction: Model<TransactionDoc> =
  (models.Transaction as Model<TransactionDoc>) ??
  model<TransactionDoc>("Transaction", TransactionSchema);
