# 06 — Authentication & Billing

## Authentication Architecture

### JWT Token Flow

```
1. User registers/logs in → API returns access_token (15 min) + refresh_token (7 days)
2. Frontend stores tokens in httpOnly cookies (not localStorage — XSS protection)
3. Every API request includes: Authorization: Bearer <access_token>
4. When access_token expires → POST /auth/refresh with refresh_token
5. When refresh_token expires → user must re-login
```

### Token Structure

```python
# Access token payload
{
    "sub": "user-uuid",              # User ID
    "email": "user@example.com",
    "role": "user",                  # user | admin
    "plan": "pro",                   # Current plan name
    "team_ids": ["uuid1", "uuid2"],  # Teams the user belongs to
    "exp": 1711368000,               # 15 minutes from issue
    "iat": 1711367100,
    "type": "access"
}

# Refresh token payload
{
    "sub": "user-uuid",
    "exp": 1711972800,               # 7 days from issue
    "iat": 1711367100,
    "type": "refresh",
    "jti": "unique-token-id"         # For revocation
}
```

### Implementation

```python
# saas/services/auth_service.py

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

SECRET_KEY = settings.JWT_SECRET_KEY      # 256-bit random, from env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "plan": user.subscription.plan.name if user.subscription else "free",
        "team_ids": [str(m.team_id) for m in user.team_memberships],
        "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

### OAuth2 Social Login (Google, GitHub)

```python
# saas/api/v1/auth.py

from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")

    # Find or create user
    user = db.query(User).join(OAuthConnection).filter(
        OAuthConnection.provider == "google",
        OAuthConnection.provider_user_id == userinfo["sub"],
    ).first()

    if not user:
        user = User(
            email=userinfo["email"],
            display_name=userinfo["name"],
            avatar_url=userinfo.get("picture"),
            email_verified=True,
        )
        db.add(user)
        db.flush()

        # Create Stripe customer
        stripe_customer = stripe.Customer.create(email=user.email)
        user.stripe_customer_id = stripe_customer.id

        # Create free subscription
        _create_free_subscription(db, user)

        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider="google",
            provider_user_id=userinfo["sub"],
        )
        db.add(oauth_conn)
        db.commit()

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Redirect to frontend with tokens
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
    )
```

### API Key Authentication (Programmatic Access)

For agency/enterprise users who want to integrate via API:

```python
# saas/api/deps.py

async def get_current_user(
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via JWT Bearer token or API key."""

    if x_api_key:
        # API key auth (sf_live_xxxx or sf_test_xxxx)
        prefix = x_api_key[:8]
        key_record = db.query(UserAPIKey).filter(
            UserAPIKey.key_prefix == prefix,
            UserAPIKey.is_active == True,
        ).first()

        if key_record and bcrypt.checkpw(x_api_key.encode(), key_record.key_hash.encode()):
            key_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return key_record.user
        raise HTTPException(401, "Invalid API key")

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = verify_token(token)
            if payload.get("type") != "access":
                raise HTTPException(401, "Invalid token type")
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user and user.is_active:
                return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")

    raise HTTPException(401, "Authentication required")
```

---

## Billing Architecture (Stripe)

### Plan Configuration in Stripe

Create these products and prices in Stripe Dashboard or via API:

```python
# One-time setup script: scripts/setup_stripe_plans.py

import stripe

stripe.api_key = "sk_live_..."

products = {
    "creator": {
        "name": "Creator Plan",
        "price": 1900,       # $19.00
        "interval": "month",
    },
    "pro": {
        "name": "Pro Plan",
        "price": 4900,       # $49.00
        "interval": "month",
    },
    "agency": {
        "name": "Agency Plan",
        "price": 14900,      # $149.00
        "interval": "month",
    },
}

for key, plan in products.items():
    product = stripe.Product.create(
        name=plan["name"],
        metadata={"plan_key": key},
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=plan["price"],
        currency="usd",
        recurring={"interval": plan["interval"]},
    )
    print(f"{key}: product={product.id}, price={price.id}")

# Create metered price for overage
for key, overage_cents in [("creator", 75), ("pro", 60), ("agency", 40)]:
    meter_price = stripe.Price.create(
        product=product.id,  # Use respective product
        currency="usd",
        recurring={"interval": "month", "usage_type": "metered"},
        unit_amount=overage_cents,
        metadata={"type": "overage", "plan_key": key},
    )
    print(f"{key}_overage: price={meter_price.id}")
```

### Checkout Flow

```python
# saas/services/billing_service.py

import stripe

class BillingService:
    def __init__(self, db: Session):
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(self, user: User, plan_name: str) -> str:
        """Create a Stripe Checkout session for plan subscription."""
        plan = self.db.query(Plan).filter(Plan.name == plan_name).first()
        if not plan or not plan.stripe_price_id:
            raise ValueError(f"Invalid plan: {plan_name}")

        # Ensure Stripe customer exists
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.display_name,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            self.db.commit()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/billing/canceled",
            metadata={"user_id": str(user.id), "plan": plan_name},
            subscription_data={
                "metadata": {"user_id": str(user.id), "plan": plan_name},
            },
        )
        return session.url

    def create_portal_session(self, user: User) -> str:
        """Create Stripe Customer Portal session for self-service billing management."""
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return session.url

    def record_usage(self, user: User, quantity: int = 1):
        """Report metered usage for overage billing."""
        sub = self.db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if not sub or not sub.stripe_subscription_id:
            return

        # Find metered subscription item
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
        for item in stripe_sub["items"]["data"]:
            price = item["price"]
            if price.get("recurring", {}).get("usage_type") == "metered":
                stripe.SubscriptionItem.create_usage_record(
                    item["id"],
                    quantity=quantity,
                    timestamp=int(datetime.now(timezone.utc).timestamp()),
                )
                break
```

### Stripe Webhook Handler

```python
# saas/api/v1/webhooks.py

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.created":
        await _handle_subscription_created(db, data)

    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)

    elif event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(db, data)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

    return {"status": "ok"}


async def _handle_subscription_created(db: Session, stripe_sub: dict):
    """Activate subscription when Stripe confirms creation."""
    user_id = stripe_sub["metadata"]["user_id"]
    plan_name = stripe_sub["metadata"]["plan"]

    user = db.query(User).filter(User.id == user_id).first()
    plan = db.query(Plan).filter(Plan.name == plan_name).first()

    if user and plan:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            sub.plan_id = plan.id
            sub.stripe_subscription_id = stripe_sub["id"]
            sub.status = stripe_sub["status"]
            sub.current_period_start = datetime.fromtimestamp(
                stripe_sub["current_period_start"], tz=timezone.utc
            )
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"], tz=timezone.utc
            )
        else:
            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                stripe_subscription_id=stripe_sub["id"],
                status=stripe_sub["status"],
            )
            db.add(sub)

        # Create usage record for this period
        _ensure_usage_record(db, user, plan)
        db.commit()


async def _handle_subscription_deleted(db: Session, stripe_sub: dict):
    """Downgrade to free when subscription is canceled."""
    user_id = stripe_sub["metadata"].get("user_id")
    if not user_id:
        return

    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub["id"]
    ).first()

    if sub and free_plan:
        sub.plan_id = free_plan.id
        sub.status = "canceled"
        sub.stripe_subscription_id = None
        db.commit()


async def _handle_payment_failed(db: Session, invoice: dict):
    """Handle failed payment — notify user, set grace period."""
    customer_id = invoice["customer"]
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            sub.status = "past_due"
            db.commit()

        # TODO: Send email notification about payment failure
```

### Usage Tracking & Limit Enforcement

```python
# saas/services/usage_service.py

class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def check_can_create_job(self, user: User) -> tuple[bool, str]:
        """Check if user can create a new video generation job.

        Returns (can_create, reason_if_not).
        """
        sub = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()

        if not sub:
            return False, "No active subscription"

        plan = sub.plan
        if plan.videos_per_month == -1:  # Unlimited
            return True, ""

        usage = self._get_current_usage(user)
        if usage.videos_created >= plan.videos_per_month:
            if plan.overage_cents > 0:
                # Allow overage if plan supports it (paid tiers)
                return True, "overage"
            else:
                # Free tier — hard limit
                return False, f"Free plan limit reached ({plan.videos_per_month} videos/month)"

        return True, ""

    def increment_usage(self, user: User, cost_usd: float = 0):
        """Record a video creation. Call after job completes."""
        usage = self._get_current_usage(user)
        usage.videos_created += 1
        usage.total_api_cost += cost_usd

        plan = self.db.query(Plan).join(Subscription).filter(
            Subscription.user_id == user.id
        ).first()

        if plan and usage.videos_created > plan.videos_per_month and plan.videos_per_month > 0:
            usage.overage_count += 1
            # Report to Stripe metered billing
            BillingService(self.db).record_usage(user, quantity=1)

        self.db.commit()

    def _get_current_usage(self, user: User) -> UsageRecord:
        """Get or create usage record for current billing period."""
        today = datetime.now(timezone.utc).date()
        period_start = today.replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        usage = self.db.query(UsageRecord).filter(
            UsageRecord.user_id == user.id,
            UsageRecord.period_start == period_start,
        ).first()

        if not usage:
            plan = self.db.query(Plan).join(Subscription).filter(
                Subscription.user_id == user.id
            ).first()

            usage = UsageRecord(
                user_id=user.id,
                period_start=period_start,
                period_end=period_end,
                videos_limit=plan.videos_per_month if plan else 3,
            )
            self.db.add(usage)
            self.db.commit()

        return usage

    def check_channel_limit(self, user: User) -> tuple[bool, str]:
        """Check if user can connect another YouTube channel."""
        plan = self.db.query(Plan).join(Subscription).filter(
            Subscription.user_id == user.id
        ).first()

        if not plan:
            return False, "No active subscription"

        if plan.channels_limit == -1:  # Unlimited
            return True, ""

        current_channels = self.db.query(YouTubeChannel).filter(
            YouTubeChannel.user_id == user.id,
            YouTubeChannel.is_active == True,
        ).count()

        if current_channels >= plan.channels_limit:
            return False, f"Channel limit reached ({plan.channels_limit}). Upgrade your plan."

        return True, ""

    def check_team_seats(self, team: Team) -> tuple[bool, str]:
        """Check if team can add another member."""
        owner = team.owner
        plan = self.db.query(Plan).join(Subscription).filter(
            Subscription.user_id == owner.id
        ).first()

        if not plan:
            return False, "No active subscription"

        if plan.team_seats == -1:  # Unlimited
            return True, ""

        current_members = self.db.query(TeamMember).filter(
            TeamMember.team_id == team.id
        ).count()

        if current_members >= plan.team_seats:
            return False, f"Team seat limit reached ({plan.team_seats}). Upgrade your plan."

        return True, ""
```

---

## API Key Encryption

All sensitive keys (BYOK API keys, YouTube OAuth tokens) are encrypted at rest
using Fernet symmetric encryption:

```python
# saas/utils/encryption.py

from cryptography.fernet import Fernet

# ENCRYPTION_KEY must be a 32-byte URL-safe base64-encoded key
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Store in environment variable, NEVER in code

_fernet = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        from saas.settings import settings
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet

def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    return get_fernet().encrypt(plaintext.encode()).decode()

def decrypt_value(ciphertext: str) -> str:
    """Decrypt a previously encrypted value."""
    return get_fernet().decrypt(ciphertext.encode()).decode()
```

---

## Dependencies to Add

```
# requirements-saas.txt
fastapi>=0.110.0,<1.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.0,<3.0
alembic>=1.13.0,<2.0
asyncpg>=0.29.0                    # Async PostgreSQL driver
psycopg2-binary>=2.9.0            # Sync PostgreSQL driver (for Alembic)
redis>=5.0.0,<6.0
celery[redis]>=5.3.0,<6.0
stripe>=8.0.0,<9.0
pyjwt>=2.8.0,<3.0
bcrypt>=4.1.0,<5.0
cryptography>=42.0.0,<43.0
authlib>=1.3.0,<2.0                # OAuth2 social login
httpx>=0.27.0,<1.0                 # Async HTTP client
python-multipart>=0.0.7            # File uploads in FastAPI
pydantic-settings>=2.0.0,<3.0     # Settings from environment
sentry-sdk[fastapi]>=1.40.0       # Error tracking
```
