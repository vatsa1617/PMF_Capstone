# PMF Dashboard - Sustainable Packaging Innovation

A comprehensive Product-Market Fit (PMF) scoring and visualization platform for analyzing sustainable packaging technologies across different markets.

## Features

- 🔐 **Secure Authentication**: Token-based login system
- 📊 **Interactive Heat Map**: Visualize PMF scores by market × technology
- 📈 **Detailed Analytics**: Drill-down views with scoring breakdowns
- 🎯 **Confidence Metrics**: Visual indicators for data reliability
- 📱 **Responsive Design**: Works on desktop and mobile
- ☁️ **Cloud-Ready**: Deploy to Netlify with zero configuration

## Quick Start

### Local Development

**Prerequisites:**
- Node.js 18+ ([Download](https://nodejs.org/))
- Python 3.9+ ([Download](https://www.python.org/))

**Setup:**

```bash
# Clone the repository
cd PMF_Capstone

# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt

# Start backend (from backend directory)
python3 app.py
# Backend runs on http://localhost:5001

# In another terminal, start frontend (from root)
cd frontend
npm run dev
# Frontend runs on http://localhost:5175
```

**Login:**
- **User ID**: `PMF_CAPSTONE`
- **Password**: `Virginia@1234`

### Deploy to Netlify

See [NETLIFY_DEPLOYMENT.md](./NETLIFY_DEPLOYMENT.md) for detailed deployment instructions.

**Quick deploy:**
1. Push code to GitHub
2. Connect repo to Netlify
3. Deploy with one click

## Project Structure

```
PMF_Capstone/
├── frontend/                 # React + Vite application
│   ├── src/
│   │   ├── App.jsx          # Main app component
│   │   ├── LoginPage.jsx    # Login screen
│   │   └── PMFDashboard.jsx # Main dashboard
│   ├── package.json
│   └── vite.config.js
├── backend/                  # Python Flask API (local dev)
│   ├── app.py               # Flask server
│   ├── auth.py              # Authentication logic
│   ├── requirements.txt
│   └── output/              # CSV/JSON data files
├── netlify/
│   └── functions/           # Netlify serverless functions
│       ├── auth-login.js
│       ├── pmf-scores.js
│       ├── pmf-summary.js
│       └── utils.js
├── netlify.toml             # Netlify configuration
└── NETLIFY_DEPLOYMENT.md    # Deployment guide
```

## API Endpoints

### Authentication

**POST** `/api/auth-login`
```bash
curl -X POST http://localhost:5001/api/auth-login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "PMF_CAPSTONE", "password": "Virginia@1234"}'
```

### Protected Endpoints

**GET** `/api/pmf-scores`
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/pmf/scores
```

**GET** `/api/pmf-summary`
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/pmf/summary
```

## Dashboard Features

### Heat Map
- Color-coded cells representing PMF scores
- Opacity indicates confidence level
- Click cells to view detailed analysis

### Filters
- Filter by PMF score range
- Filter by confidence level

### Drill-Down Analysis
- Score component breakdown (Desirability, Feasibility, Viability, Risk)
- Evidence summary
- Recommended actions (Invest, Accelerate, Monitor, Pause)

### Summary Statistics
- High PMF count
- High confidence count
- Average PMF score
- Average confidence level
- High potential/low confidence opportunities

## Scoring Methodology

PMF Score = (Desirability × 0.30) + (Feasibility × 0.30) + (Viability × 0.25) - (Risk Penalty × 0.15)

**Components:**
- **Desirability (30%)**: Market demand for the solution
- **Feasibility (30%)**: Technical feasibility
- **Viability (25%)**: Business viability and profitability
- **Risk Penalty (15%)**: Regulatory, environmental, or competitive risks

**Confidence Levels:**
- ★★★ High (70-100)
- ★★☆ Medium (40-70)
- ★☆☆ Low (0-40)

## Development

### Build for Production

```bash
# Frontend
cd frontend
npm run build
# Outputs to frontend/dist

# Backend (local deployment)
# No additional build step needed
```

### Environment Variables

Create `.env` file in root:
```
REACT_APP_API_URL=/api
```

### Testing Authentication Locally

```bash
# Test login
curl -X POST http://localhost:5001/api/auth-login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "PMF_CAPSTONE", "password": "Virginia@1234"}'

# Test protected endpoint with token
curl -H "Authorization: Bearer TOKEN_HERE" \
  http://localhost:5001/api/pmf/scores
```

## Technology Stack

**Frontend:**
- React 18
- Vite 4
- CSS3 with responsive design

**Backend (Local Dev):**
- Flask 2.3
- Flask-CORS 4.0
- Pandas 2.0

**Backend (Production - Netlify):**
- Netlify Functions (Node.js)
- Serverless API endpoints

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari 14+
- Edge (latest)

## Security

- Token-based authentication with 24-hour expiration
- Password hashing using SHA256
- CORS protection
- Authorization header validation on protected endpoints

**For Production:**
- Use environment variables for credentials
- Implement database for user management
- Use HTTPS only
- Consider OAuth/SAML integration
- Implement rate limiting

## Troubleshooting

### "Connection error. Please check if the server is running."
- Ensure backend is running: `python3 app.py`
- Check port 5001 is available: `lsof -i :5001`
- Check network connectivity

### CORS errors
- Ensure Flask-CORS is installed: `pip install Flask-CORS`
- Verify frontend URL matches CORS configuration

### Import errors
- Install dependencies: `pip install -r requirements.txt`
- Use Python 3.9+: `python3 --version`

## Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Create Pull Request

## License

Proprietary - Sustainable Packaging Innovation Initiative

## Support

For deployment issues, see [NETLIFY_DEPLOYMENT.md](./NETLIFY_DEPLOYMENT.md)

For development questions or bug reports, contact the team.

## Changelog

### v1.0.0 - Initial Release
- ✅ React dashboard with heat map
- ✅ Token-based authentication
- ✅ Protected API endpoints
- ✅ Netlify deployment ready
- ✅ Responsive design
- ✅ Drill-down analysis views