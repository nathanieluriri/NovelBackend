from enum import Enum
import os
import time

from dotenv import load_dotenv

from schemas.imports import *

load_dotenv()
FLW_WEBHOOK_SECRET_HASH = os.getenv("FLW_WEBHOOK_SECRET_HASH")


class TransactionType(str, Enum):
    real_cash = "cash"
    star_currency_transfer = "transferOfStarCurrencyBetweenAccounts"
    chapter_purchase = "transferOfStarCurrencyForChapterAccess"
    subscription_purchase = "subscriptionPurchase"


class BundleType(str, Enum):
    cash_to_star = "cash"
    star_to_book = "purchaseOfBooks"
    star_to_star = "transferringStarsToOtherUsers"
    cash_promo = "cashPromo"
    book_promo = "bookPromo"
    subscription = "subscription"


class PaymentProvider(str, Enum):
    flutterwave = "flutterwave"
    paystack = "paystack"
    stripe = "stripe"


class PaymentStatus(str, Enum):
    initiated = "initiated"
    pending = "pending"
    verified = "verified"
    fulfilled = "fulfilled"
    failed = "failed"


class EntitlementGrantType(str, Enum):
    chapter_unlock = "chapter_unlock"
    subscription = "subscription"
    wallet_credit = "wallet_credit"


class CheckoutCreateRequest(BaseModel):
    bundleId: str
    countryCode: str = Field(..., min_length=2, max_length=2)
    provider: Optional[PaymentProvider] = None
    chapterId: Optional[str] = None
    successUrl: Optional[str] = None
    cancelUrl: Optional[str] = None

    @model_validator(mode="after")
    def validate_ids(self):
        if len(self.bundleId) != 24:
            raise ValueError("bundleId must be exactly 24 characters long")
        if self.chapterId is not None and len(self.chapterId) != 24:
            raise ValueError("chapterId must be exactly 24 characters long")
        self.countryCode = self.countryCode.upper()
        return self


class CheckoutSessionOut(BaseModel):
    checkoutUrl: str
    provider: PaymentProvider
    providerReference: str
    txRef: str
    status: PaymentStatus = PaymentStatus.pending
    expiresAt: Optional[str] = None


class NormalizedWebhookEvent(BaseModel):
    provider: PaymentProvider
    eventId: str
    txRef: Optional[str] = None
    providerReference: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: str
    raw: dict


class VerificationResult(BaseModel):
    verified: bool
    providerReference: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    txRef: Optional[str] = None
    reason: Optional[str] = None


class PaymentRuntime(BaseModel):
    txRef: str
    userId: str
    bundleId: str
    chapterId: Optional[str] = None
    provider: PaymentProvider
    providerReference: Optional[str] = None
    countryCode: str
    currency: str
    amount: float
    status: PaymentStatus = PaymentStatus.initiated
    createdAt: Optional[str] = datetime.now(timezone.utc).isoformat()
    updatedAt: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode="before")
    def set_dates(cls, values):
        now = datetime.now(timezone.utc).isoformat()
        values.setdefault("createdAt", now)
        values["updatedAt"] = now
        return values


class PaymentRuntimeOut(PaymentRuntime):
    id: Optional[str] = None

    @model_validator(mode="before")
    def set_id(cls, values):
        values["id"] = str(values.get("_id"))
        return values


class WebhookEventRecord(BaseModel):
    provider: PaymentProvider
    eventId: str
    txRef: Optional[str] = None
    providerReference: Optional[str] = None
    receivedAt: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode="before")
    def set_dates(cls, values):
        values["receivedAt"] = datetime.now(timezone.utc).isoformat()
        return values


# Legacy models retained for compatibility wrappers.
class TransactionIn(BaseModel):
    userId: str
    numberOfStars: Optional[int] = None
    TransactionType: TransactionType
    amount: Optional[int] = None
    paymentId: str
    dateCreated: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode='before')
    def set_dates(cls, values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated'] = now_str
        return values


class TransactionOut(BaseModel):
    id: str
    userId: str
    paymentId: str
    numberOfStars: int
    TransactionType: TransactionType
    amount: int
    dateCreated: str

    @model_validator(mode='before')
    def set_id(cls, values):
        values['id'] = str(values.get('_id'))
        return values


class PaymentBundles(BaseModel):
    bundleType: BundleType
    amount: int
    numberOfstars: Optional[int] = None
    durationDays: Optional[int] = None
    description: str


class PaymentLink(BaseModel):
    bundle_id: str


class ChapterPayment(BaseModel):
    bundle_id: str
    chapterId: str


class PaymentBundlesUpdate(BaseModel):
    amount: Optional[int] = None
    bundleType: Optional[BundleType] = None
    numberOfstars: Optional[int] = None
    durationDays: Optional[int] = None
    description: Optional[str] = None


class PaymentBundlesOut(BaseModel):
    id: str
    amount: int
    numberOfstars: Optional[int] = None
    bundleType: Optional[BundleType] = None
    durationDays: Optional[int] = None
    description: str
    dateCreated: int

    @model_validator(mode='before')
    def set_id(cls, values):
        values['id'] = str(values.get('_id'))
        return values
