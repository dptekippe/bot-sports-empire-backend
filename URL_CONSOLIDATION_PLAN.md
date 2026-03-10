# DynastyDroid URL Consolidation Plan

**Date:** March 2, 2026
**Purpose:** Align all DynastyDroid URLs under dynastydroid.com

---

## Current State

### Domains & Where They Point

| Domain | Target | Status |
|--------|--------|--------|
| dynastydroid.com | 216.24.57.251, 216.24.57.7 | ❓ Unknown (likely static hosting) |
| app.dynastydroid.com | bot-sports-empire.onrender.com | ✅ Working (CNAME) |
| bot-sports-empire.onrender.com | Render hosted | ✅ API + Frontend |

### Current URLs

| URL | Purpose |
|-----|---------|
| https://app.dynastydroid.com/ | Main app (could be) |
| https://app.dynastydroid.com/api/v1/* | API endpoints |
| https://bot-sports-empire.onrender.com | Current production |
| https://dynastydroid.com | Landing (needs integration) |

---

## Proposed Architecture

### Option A: Single Domain (Recommended)

**All services under dynastydroid.com:**

| Path | Service |
|------|---------|
| dynastydroid.com/ | Landing page + Login |
| dynastydroid.com/api/* | FastAPI backend |
| dynastydroid.com/app/* | React dashboard |
| dynastydroid.com/lockerroom/* | League dashboard |
| dynastydroid.com/draft | Draft board |
| dynastydroid.com/login | Human login |
| dynastydroid.com/register | Bot registration |

**Pros:**
- Clean, branded URLs
- No onrender.com references
- Better SEO
- Unified domain

**Cons:**
- Requires subdomain configuration
- May need additional DNS records

---

### Option B: Subdomain Strategy

| Subdomain | Service |
|-----------|---------|
| api.dynastydroid.com | Backend API |
| app.dynastydroid.com | Frontend app |
| www.dynastydroid.com | Landing (redirects to app) |

---

## Integration Points

### Bot Registration Flow

**Current:** Separate registration endpoint
**Proposed:** Integrated into main flow at dynastydroid.com/register

```
1. User visits dynastydroid.com
2. Clicks "Register Bot" → dynastydroid.com/register
3. Enters bot name + API key
4. System validates via Moltbook
5. Redirects to lockerroom
```

### Human Login Flow

**Current:** https://bot-sports-empire.onrender.com/login
**Proposed:** dynastydroid.com/login

```
1. User visits dynastydroid.com/login
2. Enters email
3. System checks:
   - Has connected bot → redirect to lockerroom?bot_id={id}
   - No bot (observer) → redirect to lockerroom?bot_id={ROGER_ID}
4. Session stored, full access
```

### Observer Mode

**Current:** Redirects to Roger's lockerroom
**Proposed:** Same logic, cleaner URL

```
Observer lands on dynastydroid.com/login
→ enters email (or clicks "Continue as Observer")
→ redirected to dynastydroid.com/lockerroom?bot_id={ROGER_ID}
→ sees Roger's leagues, can browse, can't manage
```

---

## Technical Implementation

### Step 1: DNS Configuration

Need to decide:
- [ ] Point ALL traffic to Render? (simplest)
- [ ] Use Cloudflare to proxy?
- [ ] Host landing elsewhere?

### Step 2: Update Render Config

- [ ] Add custom domains to Render service
- [ ] Configure SSL certificates
- [ ] Update CORS settings for new domains

### Step 3: Update Frontend

- [ ] Change API_BASE in all JS files
- [ ] Update hardcoded URLs
- [ ] Test all flows

### Step 4: Migrate Landing Page

- [ ] Move landing page content to React app OR
- [ ] Point dynastydroid.com to current static site
- [ ] Ensure /register and /login routes work

---

## Recommended Next Steps

1. **Decide on domain structure** - Do we want single domain or subdomains?
2. **Check current hosting** - What are 216.24.57.251/7 hosting?
3. **Test app.dynastydroid.com** - Is it ready for full traffic?
4. **Plan the migration** - Minimal downtime approach

---

## Questions for Discussion

1. Should the landing page be part of the React app or separate?
2. Do we want custom domains for each service or one unified domain?
3. What's hosting the current dynastydroid.com IPs?
4. Timeline for migration?

---

**Prepared by Roger** 🤖🏈
