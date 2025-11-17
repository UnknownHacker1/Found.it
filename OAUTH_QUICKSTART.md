# OAuth Quick Start - TL;DR

## Just Want to Demo? Use Guest Mode

1. Start backend: `cd backend && python app.py`
2. Start frontend: `cd frontend && npm start`
3. Click **"Continue without login"** on the login page
4. Done! ✅

---

## Want Real OAuth Login?

### 5-Minute Setup:

1. **Get Google OAuth credentials:**
   - Go to https://console.cloud.google.com/
   - Create new project → APIs & Services → Credentials
   - Create OAuth client ID (Web application)
   - Add redirect URI: `http://localhost:8001/auth/callback`
   - Copy Client ID and Client Secret

2. **Update backend config:**
   ```bash
   # Edit backend/config.py
   GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET = "your-client-secret"
   ```

3. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Start the app:**
   ```bash
   # Terminal 1
   cd backend
   python app.py

   # Terminal 2
   cd frontend
   npm start
   ```

5. **Login with Google:**
   - Click "Continue with Google"
   - Sign in with your Google account
   - Done! Your profile appears in the sidebar

---

## Full Instructions

See [OAUTH_SETUP.md](OAUTH_SETUP.md) for detailed step-by-step guide.

---

## What You Get

✅ Professional login page with Google OAuth
✅ User authentication and session management
✅ User profile display (name, email, picture)
✅ JWT token-based security
✅ Ready for user tracking in paid service
✅ Guest mode for quick testing

Perfect for demos! 🎉
