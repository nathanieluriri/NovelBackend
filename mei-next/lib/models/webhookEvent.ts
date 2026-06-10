import { Schema, model, models, type Model } from "mongoose";

/** Loose doc type at the seam — legacy data is heterogeneous. */
export type WebhookEventDoc = Record<string, any>;

const WebhookEventSchema = new Schema<WebhookEventDoc>(
  {
    provider: { type: String, enum: ["flutterwave", "paystack", "stripe"], required: true },
    eventId: { type: String, required: true },
    txRef: { type: String, default: null },
    providerReference: { type: String, default: null },
    receivedAt: { type: String },
  },
  { collection: "payment_webhook_events", versionKey: false, strict: true, autoIndex: false },
);

WebhookEventSchema.index({ provider: 1, eventId: 1 }, { unique: true });

export const WebhookEvent: Model<WebhookEventDoc> =
  (models.WebhookEvent as Model<WebhookEventDoc>) ??
  model<WebhookEventDoc>("WebhookEvent", WebhookEventSchema);
