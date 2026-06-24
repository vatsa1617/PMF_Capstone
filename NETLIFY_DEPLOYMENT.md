# Netlify Deployment Guide

This project is configured for seamless deployment to Netlify using Netlify Functions for the backend API.

## Architecture

- **Frontend**: React + Vite (deployed as static site)
- **Backend**: Netlify Functions (serverless Node.js endpoints)
- **Database**: Local JSON files (served from build output)

## Prerequisites

1. **GitHub Account**: Repository must be pushed to GitHub
2. **Netlify Account**: Create free account at https://app.netlify.com
3. **Node.js**: Version 18+ installed locally

## Deployment Steps

### 1. Push Code to GitHub

```bash
cd PMF_Capstone
git remote add origin https://github.com/vatsa1617/PMF_Capstone.git
git push -u origin main
```

### 2. Connect to Netlify

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import an existing project"
3. Select GitHub and authorize Netlify
4. Choose the `PMF_Capstone` repository
5. Configure build settings:
   - **Base directory**: Leave empty (or .)
   - **Build command**: `cd frontend && npm run build`
   - **Publish directory**: `frontend/dist`
6. Click "Deploy site"

### 3. Configure Environment Variables (Optional)

In Netlify dashboard:
1. Go to Site settings → Build & deploy → Environment
2. Add any environment variables (currently none required)

## How It Works

### URL Structure

- **Frontend**: `https://your-site.netlify.app/`
- **API Endpoints**: `https://your-site.netlify.app/api/*`

### Netlify Redirects

The `netlify.toml` file includes:
- API redirect rule: `/api/*` → `/.netlify/functions/:splat`
- SPA fallback: `/*` → `/index.html` (for React routing)

### Authentication Flow

1. User submits login at `/api/auth-login`
2. Netlify Function validates credentials
3. Returns JWT token valid for 24 hours
4. Frontend stores token in localStorage
5. Subsequent API calls include `Authorization: Bearer <token>` header

## Netlify Functions

Located in `netlify/functions/`:

- **auth-login.js**: Authentication endpoint
- **pmf-scores.js**: Get PMF scoring matrix
- **pmf-summary.js**: Get scoring summary
- **health.js**: Health check endpoint
- **utils.js**: Shared utilities (auth, CORS headers)

## Data Files

The backend reads from CSV/JSON files in `backend/output/`:
- `agent4_pmf_matrix.csv` - PMF scoring data
- `agent4_summary.json` - Summary statistics

These files are included in the build and served by Netlify Functions.

## Local Development

For local testing before deployment:

```bash
# Install dependencies
npm install
cd frontend && npm install
cd ../backend && pip install -r requirements.txt

# Start local servers
npm run dev  # Runs Vite on http://localhost:5175
# In another terminal:
python3 app.py  # Runs Flask on http://localhost:5001
```

Update environment variable if needed:
```bash
export REACT_APP_API_URL=http://localhost:5001
```

## Troubleshooting

### Functions not working
- Check `netlify/functions/` directory exists
- Verify function names match routes in `netlify.toml`
- Check Netlify build logs for errors

### API calls failing
- Verify `netlify.toml` redirects are correct
- Check browser console for CORS issues
- Confirm authentication token is being sent

### Build failures
- Ensure Node.js 18+ is used
- Check `frontend/package.json` has all dependencies
- Verify build command in `netlify.toml` matches your setup

## API Endpoints

### POST /api/auth-login
Login with credentials

**Request:**
```json
{
  "user_id": "PMF_CAPSTONE",
  "password": "Virginia@1234"
}
```

**Response:**
```json
{
  "status": "success",
  "token": "...",
  "user_id": "PMF_CAPSTONE"
}
```

### GET /api/pmf-scores
Get PMF scoring matrix (requires auth)

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "success",
  "data": [...],
  "count": 6
}
```

### GET /api/pmf-summary
Get summary statistics (requires auth)

**Headers:** `Authorization: Bearer <token>`

### GET /api/health
Health check (no auth required)

## Production Notes

- Tokens expire after 24 hours
- Credentials are hardcoded in `netlify/functions/auth-login.js`
- For production: Use environment variables for credentials
- Consider using Netlify Identity for user management

## Support

For issues with Netlify deployment, check:
- https://docs.netlify.com/functions/overview/
- https://docs.netlify.com/routing/redirects/
- Netlify build logs in dashboard
