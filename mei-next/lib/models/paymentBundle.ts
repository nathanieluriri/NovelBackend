import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type PaymentBundleDoc = Record<string, any>;

const PaymentBundleSchema = new Schema<PaymentBundleDoc>(
  {
    bundleType: {
      type: String,
      required: true,
      enum: [
        "cash",
        "purchaseOfBooks",
        "transferringStarsToOtherUsers",
        "cashPromo",
        "bookPromo",
        "subscription", // normalized to "subscriptionCash" on validation/read (service layer)
        "subscriptionCash",
        "subscriptionStars",
      ],
    },
    amount: { type: Number, default: null }, // cash, major units
    numberOfstars: { type: Number, default: null },
    durationDays: { type: Number, default: null }, // subscriptions
    description: { type: String, required: true },
    dateCreated: { type: Number }, // epoch seconds
    dateUpdated: { type: Number }, // epoch seconds
  },
  { collection: "payments", versionKey: false, strict: true, autoIndex: false },
);

export const PaymentBundle: Model<PaymentBundleDoc> =
  (models.PaymentBundle as Model<PaymentBundleDoc>) ??
  model<PaymentBundleDoc>("PaymentBundle", PaymentBundleSchema);
