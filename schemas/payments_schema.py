from enum import Enum
import os
import time

from dotenv import load_dotenv
from pydantic import AliasChoices, Field

from schemas.imports import *
from schemas.utils import normalize_datetime_to_iso

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
    subscription_cash = "subscriptionCash"
    subscription_stars = "subscriptionStars"


SUBSCRIPTION_CASH_TYPES = {
    BundleType.subscription,
    BundleType.subscription_cash,
}
SUBSCRIPTION_STAR_TYPES = {
    BundleType.subscription_stars,
}
SUBSCRIPTION_TYPES = SUBSCRIPTION_CASH_TYPES | SUBSCRIPTION_STAR_TYPES


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
    amount: Optional[int] = None
    numberOfstars: Optional[int] = None
    durationDays: Optional[int] = None
    description: str

    @model_validator(mode="before")
    def normalize_legacy_fields(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values
        normalized = dict(values)
        if normalized.get("bundleType") == BundleType.subscription.value:
            normalized["bundleType"] = BundleType.subscription_cash.value
        return normalized

    @model_validator(mode="after")
    def validate_for_bundle_type(self):
        if self.amount is not None and self.amount < 0:
            raise ValueError("amount cannot be negative")
        if self.numberOfstars is not None and self.numberOfstars < 0:
            raise ValueError("numberOfstars cannot be negative")
        if self.durationDays is not None and self.durationDays <= 0:
            raise ValueError("durationDays must be greater than 0")

        if self.bundleType in SUBSCRIPTION_CASH_TYPES:
            if self.amount is None or self.amount <= 0:
                raise ValueError("Cash subscription bundle requires amount > 0")
            if self.durationDays is None or self.durationDays <= 0:
                raise ValueError("Cash subscription bundle requires durationDays > 0")
            if self.numberOfstars not in (None, 0):
                raise ValueError("Cash subscription bundle must not set numberOfstars")
            return self

        if self.bundleType in SUBSCRIPTION_STAR_TYPES:
            if self.numberOfstars is None or self.numberOfstars <= 0:
                raise ValueError("Stars subscription bundle requires numberOfstars > 0")
            if self.durationDays is None or self.durationDays <= 0:
                raise ValueError("Stars subscription bundle requires durationDays > 0")
            if self.amount not in (None, 0):
                raise ValueError("Stars subscription bundle must not set amount")
            return self

        if self.amount is None or self.amount <= 0:
            raise ValueError("amount must be greater than 0")

        if self.bundleType in {BundleType.cash_to_star, BundleType.star_to_book}:
            if self.numberOfstars is None or self.numberOfstars <= 0:
                raise ValueError("numberOfstars must be greater than 0 for this bundle type")

        return self


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

    @model_validator(mode="before")
    def normalize_legacy_fields(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values
        normalized = dict(values)
        if normalized.get("bundleType") == BundleType.subscription.value:
            normalized["bundleType"] = BundleType.subscription_cash.value
        return normalized

    @model_validator(mode="after")
    def validate_partial_fields(self):
        if self.amount is not None and self.amount < 0:
            raise ValueError("amount cannot be negative")
        if self.numberOfstars is not None and self.numberOfstars < 0:
            raise ValueError("numberOfstars cannot be negative")
        if self.durationDays is not None and self.durationDays <= 0:
            raise ValueError("durationDays must be greater than 0")
        return self


class SubscriptionStarsPurchaseRequest(BaseModel):
    bundleId: str = Field(
        ...,
        validation_alias=AliasChoices("bundleId", "bundle_id"),
        serialization_alias="bundleId",
    )

    @model_validator(mode="after")
    def validate_bundle_id(self):
        if len(self.bundleId) != 24:
            raise ValueError("bundleId must be exactly 24 characters long")
        return self


class PricingBundleOut(BaseModel):
    id: str
    bundleType: BundleType
    description: str
    durationDays: Optional[int] = None
    cashAmount: Optional[int] = None
    starAmount: Optional[int] = None
    dateCreated: Optional[str] = None


class PricingCatalogOut(BaseModel):
    subscriptionPlans: List[PricingBundleOut] = Field(default_factory=list)
    starBundles: List[PricingBundleOut] = Field(default_factory=list)
    chapterUnlockBundles: List[PricingBundleOut] = Field(default_factory=list)


class PaymentBundlesOut(BaseModel):
    id: str
    amount: Optional[int] = None
    numberOfstars: Optional[int] = None
    bundleType: Optional[BundleType] = None
    durationDays: Optional[int] = None
    description: str
    dateCreated: Optional[str] = None

    @model_validator(mode='before')
    def set_id(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values

        normalized = dict(values)
        identifier = normalized.get("id", normalized.get("_id"))
        if identifier is not None:
            normalized["id"] = str(identifier)
        if normalized.get("bundleType") == BundleType.subscription.value:
            normalized["bundleType"] = BundleType.subscription_cash.value

        normalized["dateCreated"] = normalize_datetime_to_iso(normalized.get("dateCreated"))
        return normalized
