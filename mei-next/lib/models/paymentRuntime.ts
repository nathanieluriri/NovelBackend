import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type PaymentRuntimeDoc = Record<string, any>;

const PaymentRuntimeSchema = new Schema<PaymentRuntimeDoc>(
  {
    txRef: { type: String, required: true },
    userId: { type: String, required: true },
    bundleId: { type: String, required: true },
    chapterId: { type: String, default: null },
    provider: { type: String, enum: ["flutterwave", "paystack", "stripe"], required: true },
    providerReference: { type: String, default: null },
    countryCode: { type: String, required: true },
    currency: { type: String, required: true },
    amount: { type: Number, required: true },
    status: {
      type: String,
      enum: ["initiated", "pending", "verified", "fulfilled", "failed"],
      default: "initiated",
    },
    createdAt: { type: String },
    updatedAt: { type: String },
  },
  { collection: "payment_runtime", versionKey: false, strict: true, autoIndex: false },
);

PaymentRuntimeSchema.index({ txRef: 1 }, { unique: true });
PaymentRuntimeSchema.index({ provider: 1, providerReference: 1 }, { sparse: true });

export const PaymentRuntime: Model<PaymentRuntimeDoc> =
  (models.PaymentRuntime as Model<PaymentRuntimeDoc>) ??
  model<PaymentRuntimeDoc>("PaymentRuntime", PaymentRuntimeSchema);
