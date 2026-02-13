# PHASE 1 ACTION PLAN: Bot Owner Dashboard
**Start:** NOW | **Deadline:** 3 days

## DAY 1: Foundation (Today)
### Morning (2 hours):
1. **Setup React/Next.js project**
   - `npx create-next-app@latest bot-dashboard`
   - Configure for Render deployment
   - Set up API client (axios/fetch)

2. **Create basic layout**
   - Header with DynastyDroid logo
   - Navigation structure
   - Responsive design

### Afternoon (3 hours):
3. **Bot Registration Form**
   - Form with all required fields (name, display_name, etc.)
   - Validation matching API schema
   - API integration (POST /api/v1/bots/register)
   - Success/error handling

4. **API Key Display Component**
   - Show generated API key (copy-to-clipboard)
   - Security warnings
   - "Save this key" messaging

## DAY 2: Core Features
### Morning:
5. **Bot Management Page**
   - GET /api/v1/bots/{id} integration
   - Display bot details
   - API key rotation button

6. **Authentication Flow**
   - Bearer token storage (localStorage)
   - Protected routes
   - Login/logout

### Afternoon:
7. **League Discovery**
   - List available leagues (mock data first)
   - Filter by personality type
   - "Join League" buttons (placeholder)

## DAY 3: Polish & Deploy
### Morning:
8. **UI/UX Polish**
   - Styling matching landing page
   - Loading states
   - Error boundaries

9. **Testing**
   - End-to-end tests
   - API integration tests
   - Mobile responsiveness

### Afternoon:
10. **Deployment**
    - Deploy to Render (new service)
    - Connect to production API
    - Update landing page links

## TANGIBLE OUTPUTS (Daily):
- **EOD Today:** Working registration form on localhost
- **EOD Day 2:** Full dashboard with auth on localhost  
- **EOD Day 3:** Live production dashboard at dashboard.dynastydroid.com

## SUBAGENT ALLOCATION:
- **Frontend Agent:** React/Next.js implementation
- **API Agent:** Enhance backend endpoints as needed
- **Design Agent:** UI/UX polish
- **DevOps Agent:** Deployment pipeline

## RISKS & MITIGATION:
- **Risk:** API not fully deployed
  - **Mitigation:** Use local API for development
- **Risk:** Design delays
  - **Mitigation:** Use simple, functional UI first
- **Risk:** Authentication complexity
  - **Mitigation:** Start with basic API key storage

## SUCCESS CRITERIA:
1. ✅ Bot registration works end-to-end
2. ✅ API key management functional
3. ✅ Dashboard accessible on mobile
4. ✅ Deployed to production
5. ✅ Linked from main landing page

**Mantra:** "A working dashboard is better than a perfect plan."
