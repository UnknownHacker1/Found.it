# OAuth Setup Guide for Foundit

This guide shows how to set up Google OAuth authentication for your Foundit application.

## Why OAuth?

OAuth provides:
- **User Authentication**: Secure login with Google accounts
- **User Tracking**: Track users for future paid service
- **Professional Demo**: Shows enterprise-ready authentication

---

## Quick Start (For Demo/Development)

### Option 1: Skip OAuth (Guest Mode)

If you just want to test the app without setting up OAuth:

1. Start the app normally
2. Click **"Continue without login"** on the login page
3. Use the app as a guest

### Option 2: Set Up Google OAuth (Recommended for Demo)

Follow the steps below to enable real OAuth login.

---

## Step 1: Create Google OAuth Credentials

### 1.1 Go to Google Cloud Console

Visit: https://console.cloud.google.com/

### 1.2 Create a New Project

1. Click the project dropdown at the top
2. Click **"New Project"**
3. Name it: `Foundit` (or any name you prefer)
4. Click **"Create"**

### 1.3 Enable OAuth Consent Screen

1. In the left sidebar, go to **APIs & Services** → **OAuth consent screen**
2. Select **"External"** (for testing) or **"Internal"** (if you have Google Workspace)
3. Click **"Create"**

**Fill in the required fields:**
- **App name**: `Foundit`
- **User support email**: Your email
- **Developer contact email**: Your email

4. Click **"Save and Continue"**
5. Skip "Scopes" (click **"Save and Continue"**)
6. Add test users (your Google account email) if in testing mode
7. Click **"Save and Continue"**

### 1.4 Create OAuth Client ID

1. In the left sidebar, go to **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Select **Application type**: **"Web application"**
4. **Name**: `Foundit Desktop`

**Authorized redirect URIs:**
Add these exact URLs:
```
http://localhost:8001/auth/callback
http://localhost:8001/auth/success
```

5. Click **"Create"**

### 1.5 Download Credentials

You'll see a popup with:
- **Client ID**: `xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxxxxxxxxxxxxxx`

**Copy these values!** You'll need them in the next step.

---

## Step 2: Configure Foundit Backend

### 2.1 Edit `backend/config.py`

Open `backend/config.py` and update these lines:

```python
# Google OAuth 2.0 Configuration
GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
GOOGLE_CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"
```

Replace with your actual values from Step 1.5.

### 2.2 (Optional) Use Environment Variables

For better security, you can use environment variables instead:

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CLIENT_ID="your-client-id-here"
$env:GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_CLIENT_ID=your-client-id-here
set GOOGLE_CLIENT_SECRET=your-client-secret-here
```

**Linux/Mac:**
```bash
export GOOGLE_CLIENT_ID="your-client-id-here"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

### 2.3 Generate a JWT Secret Key

This is used to secure user sessions.

**Generate a random secret:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and update `config.py`:

```python
JWT_SECRET_KEY = "your-generated-secret-key-here"
```

Or set as environment variable:
```bash
set JWT_SECRET_KEY=your-generated-secret-key-here
```

---

## Step 3: Install Dependencies

### 3.1 Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `authlib` - OAuth client library
- `python-jose` - JWT token handling
- `python-multipart` - Form data parsing

---

## Step 4: Start the Application

### 4.1 Start Backend

```bash
cd backend
python app.py
```

Wait for:
```
✓ RAG engine ready!
Server ready!
INFO:     Uvicorn running on http://127.0.0.1:8001
```

### 4.2 Start Frontend

```bash
cd frontend
npm start
```

The Electron app will open with the **login page**.

---

## Step 5: Test OAuth Login

### 5.1 Login Flow

1. The app opens to the **login page**
2. Click **"Continue with Google"**
3. A popup window opens with Google's login screen
4. Sign in with your Google account
5. Grant permissions to Foundit
6. You'll be redirected back to the app
7. The main chat interface loads with your profile info in the sidebar

### 5.2 Guest Mode (No Login)

Alternatively, click **"Continue without login"** to use the app without authentication.

---

## Troubleshooting

### Error: "OAuth not configured"

**Cause**: `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is missing in `config.py`

**Solution**:
- Check that you updated `config.py` with your credentials
- Restart the backend server after updating

### Error: "redirect_uri_mismatch"

**Cause**: The redirect URI in Google Cloud Console doesn't match your app

**Solution**:
1. Go to Google Cloud Console → Credentials
2. Edit your OAuth client
3. Make sure these URIs are added:
   ```
   http://localhost:8001/auth/callback
   http://localhost:8001/auth/success
   ```

### Error: "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen is not configured properly

**Solution**:
1. Go to Google Cloud Console → OAuth consent screen
2. Add your email to "Test users" if app is in testing mode
3. Or publish the app (not required for personal use)

### Login window doesn't close automatically

**Cause**: Browser popup blocker or cross-origin security

**Solution**:
- Manually close the login window after seeing "Login Successful"
- Check browser console for errors
- Try restarting the app

### Backend shows "OAuth not configured" but credentials are set

**Cause**: Backend was started before updating `config.py`

**Solution**:
- Stop the backend (`Ctrl+C`)
- Restart: `python app.py`

---

## Security Best Practices

### For Demo/Development:
- ✅ Use test users in Google OAuth consent screen
- ✅ Keep credentials in `config.py` (don't commit to Git)
- ✅ Add `config.py` to `.gitignore`

### For Production:
- ✅ Use environment variables for credentials (not `config.py`)
- ✅ Generate strong JWT secret key
- ✅ Use HTTPS instead of HTTP
- ✅ Enable token rotation
- ✅ Add rate limiting to auth endpoints
- ✅ Implement user database for persistent sessions

---

## How It Works

### OAuth Flow:

```
┌─────────┐      ┌────────────┐      ┌──────────┐
│ User    │      │ Foundit    │      │ Google   │
│ (You)   │      │ Backend    │      │ OAuth    │
└─────────┘      └────────────┘      └──────────┘
     │                 │                    │
     │  Click Login    │                    │
     │────────────────>│                    │
     │                 │  Redirect to Auth  │
     │                 │───────────────────>│
     │                 │                    │
     │  <──────────────┴──────────────────  │
     │  (Google Login Page)                 │
     │                                       │
     │  Enter credentials & consent          │
     │──────────────────────────────────────>│
     │                                       │
     │  <──────────────────────────────────  │
     │  Authorization Code                   │
     │                 │                    │
     │  Send code      │                    │
     │────────────────>│                    │
     │                 │  Exchange code     │
     │                 │───────────────────>│
     │                 │  for user info     │
     │                 │<───────────────────│
     │                 │                    │
     │  JWT Token      │                    │
     │<────────────────│                    │
     │                 │                    │
     │  (Logged in!)   │                    │
     └─────────────────┴────────────────────┘
```

### JWT Token Storage:

- Token stored in browser's `localStorage`
- Included in API requests as `Authorization: Bearer <token>`
- Backend validates token on protected endpoints
- Token expires after 7 days (configurable)

---

## User Tracking for Paid Service

Once OAuth is set up, you can track users by:

1. **User ID**: `sub` field from Google (unique identifier)
2. **Email**: User's Google email
3. **Name**: User's display name
4. **Login Time**: When user authenticated

### Future: Add User Database

For a real paid service, you'd add:

```python
# Example user database (SQLite/PostgreSQL)
class User(Base):
    id = Column(Integer, primary_key=True)
    google_id = Column(String, unique=True)  # sub from Google
    email = Column(String, unique=True)
    name = Column(String)
    picture_url = Column(String)
    created_at = Column(DateTime)
    subscription_tier = Column(String)  # free, pro, enterprise
    subscription_expires = Column(DateTime)
```

Then you can:
- Track usage per user
- Implement subscription tiers
- Store user preferences
- Show personalized file history

---

## Optional: Add More OAuth Providers

Want to support Microsoft, GitHub, or other providers?

### Microsoft OAuth:

```python
# Add to auth.py
oauth.register(
    name='microsoft',
    client_id=config.MICROSOFT_CLIENT_ID,
    client_secret=config.MICROSOFT_CLIENT_SECRET,
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
```

### GitHub OAuth:

```python
# Add to auth.py
oauth.register(
    name='github',
    client_id=config.GITHUB_CLIENT_ID,
    client_secret=config.GITHUB_CLIENT_SECRET,
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    client_kwargs={'scope': 'user:email'}
)
```

---

## Next Steps

Now that OAuth is set up:

1. ✅ Test login with your Google account
2. ✅ Verify user info appears in sidebar
3. ✅ Test logout functionality
4. ✅ Try guest mode (skip login)
5. ✅ Demo to stakeholders!

For the future paid service:
- Add user database (PostgreSQL/MongoDB)
- Implement subscription tiers
- Track usage metrics
- Add payment integration (Stripe/PayPal)

---

## Need Help?

- **Google OAuth Docs**: https://developers.google.com/identity/protocols/oauth2
- **Authlib Docs**: https://docs.authlib.org/
- **FastAPI OAuth Guide**: https://fastapi.tiangolo.com/advanced/security/

Enjoy your OAuth-enabled Foundit! 🎉
