# AI SOC - Quick Start Guide

**Status**: ✅ Production Ready  
**AI Model**: Claude 4.5 Sonnet  
**Completion**: 12/12 Phases ✅

---

## 🚀 Get Started in 5 Minutes

### ⚡ One-Line Setup (Easiest!)

```bash
git clone https://github.com/your-org/ai-opensoc.git && cd ai-opensoc && ./setup_dev.sh
```

This script will:
- ✅ Copy environment files (with DEV_MODE enabled)
- ✅ Create Python virtual environment
- ✅ Install all dependencies (backend + frontend)
- ✅ Start the database
- ✅ Display next steps

**Then start the app:**
```bash
./start_web.sh          # Interactive mode
# OR
./start_daemon.sh       # Background mode
```

---

### 📋 Manual Setup

**Two ways to run AI SOC:**
1. **🐧 Linux-Native Scripts** - Faster, better for development *(Recommended)*
2. **🐳 Docker Compose** - Containerized, better for production

#### Prerequisites
- Docker & Docker Compose
- Node.js 18+ and npm (for native scripts)
- Python 3.11+ (for native scripts)
- Claude API key (Anthropic) *(optional for testing)*

#### 1. Clone & Configure

```bash
# Clone repository
git clone https://github.com/your-org/ai-opensoc.git
cd ai-opensoc

# Copy environment templates
cp .env.example .env
cp frontend/env.development.example frontend/.env.development

# Edit .env with your credentials (optional for testing)
nano .env
```

#### 2. Required Environment Variables

```bash
# Minimum required for quick start
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/deeptempo
JWT_SECRET_KEY=your-secret-key-at-least-32-characters-long
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key-here

# Optional but recommended
SPLUNK_HOST=localhost
JIRA_URL=https://your-org.atlassian.net

# ⚡ QUICK ITERATION MODE (Development Only!)
# Skip login and authentication for faster development
# WARNING: NEVER use in production!
DEV_MODE=true  # Controls BOTH backend and frontend - no separate config needed!
```

**🚀 Want to iterate quickly without login?**
Just set `DEV_MODE=true` in your root `.env` file and both backend AND frontend will bypass authentication!
- Backend: JWT auth bypassed, returns mock admin user
- Frontend: Login UI bypassed, uses mock admin user
- No separate frontend configuration needed!

See the [DEV_MODE Guide](DEV_MODE.md) for full details.

#### 3. Start Services

**Option A: Linux-Native (Faster, Recommended for Dev)** 🐧
```bash
# Interactive mode (keeps terminal open)
./start_web.sh

# OR Background mode (frees terminal)
./start_daemon.sh
```

**Option B: Docker Compose** 🐳
```bash
# Start all services with Docker Compose
cd docker
docker-compose up -d

# Check services are running
docker-compose ps

# Expected output:
# ✓ postgres (5432)
# ✓ soc-api (6987)
# ✓ soc-daemon (background)
```

**For full native scripts guide:** See [`NATIVE_SCRIPTS_GUIDE.md`](NATIVE_SCRIPTS_GUIDE.md)

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec soc-api alembic upgrade head

# Create admin user
docker-compose exec soc-api python -c "
from backend.services.auth_service import AuthService
from database.connection import get_db_session
auth = AuthService()
db = next(get_db_session())
auth.register_user(
    db=db,
    username='admin',
    email='admin@example.com',
    password='changeme123',
    role_name='admin'
)
print('Admin user created: admin / changeme123')
"
```

### 5. Start Frontend

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Frontend will be available at:
# http://localhost:6988
```

### 6. Run Tests

```bash
cd ..
chmod +x run_tests.sh
./run_tests.sh

# Expected: ✅ All tests passing
```

### 7. Access Application

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:6988 | admin / changeme123 * |
| **API** | http://localhost:6987 | - |
| **API Docs** | http://localhost:6987/docs | - |
| **Splunk** | http://localhost:6990 | admin / changeme |

\* **With DEV_MODE enabled**: No login required! You'll be automatically logged in as a mock dev user with full admin permissions. Perfect for rapid iteration!

**To enable DEV_MODE**: Add `DEV_MODE=true` to your `.env` file. See [DEV_MODE.md](DEV_MODE.md) for full details.

---

## 📱 First Steps After Login

### 1. Configure Your Profile
- Login with admin/changeme123
- Click user menu → Change Password
- Set up MFA for security

### 2. Add SIEM Connections
- Go to Settings → Integrations
- Configure your SIEM credentials:
  - Splunk
  - Azure Sentinel
  - AWS Security Hub
  - Microsoft Defender

### 3. Explore Features

**Dashboard**: Real-time SOC metrics and overview

**Cases**: View and manage security cases
- Click any case to see details
- 5 consolidated tabs: Overview, Investigation, Resolution, Collaboration, Details

**Analytics**: AI-powered insights dashboard
- Key metrics with trends
- Claude 4.5 Sonnet generated insights
- Interactive charts
- Time range selector (24h, 7d, 30d)

**AI Decisions**: Review AI recommendations

**Users**: Manage team members (admin only)

---

## 🤖 Claude 4.5 Features

The platform uses **Claude 4.5 Sonnet** for:

### 🔍 AI Insights (Analytics Page)
- Anomaly detection in SOC metrics
- Trend analysis and forecasting
- Actionable recommendations
- Confidence-scored insights

### 🔎 Case Investigation
- Automated threat analysis
- MITRE ATT&CK mapping
- Evidence correlation
- Investigation assistance

### 📊 Finding Enrichment
- Context enhancement
- Severity validation
- Threat intelligence correlation
- Attribution analysis

**All AI features use Claude 4.5 Sonnet** (claude-sonnet-4-20250514)

---

## 🧪 Quick Test

```bash
# Test API health
curl http://localhost:6987/health

# Test authentication
curl -X POST http://localhost:6987/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme123"}'

# Test analytics (with token from login)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:6987/api/analytics?timeRange=7d"

# Should return metrics and AI insights
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `PROJECT_COMPLETE.md` | Complete project summary |
| `TESTING_PLAN.md` | Comprehensive test documentation |
| `FINAL_IMPLEMENTATION_SUMMARY.md` | Technical implementation details |
| `frontend/PERFORMANCE_OPTIMIZATIONS.md` | Performance guide |
| `/docs` API endpoint | Interactive API documentation |

---

## 🔒 Security Checklist

Before going to production:

- [ ] Change default admin password
- [ ] Set strong JWT_SECRET_KEY (32+ characters)
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up MFA for all users
- [ ] Review RBAC permissions
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting
- [ ] Configure backup strategy
- [ ] Review audit logs

---

## 🐛 Troubleshooting

### Services won't start
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs soc-api
docker-compose logs soc-daemon

# Restart services
docker-compose restart
```

### Can't login
```bash
# Check if admin user exists
docker-compose exec postgres psql -U postgres -d deeptempo \
  -c "SELECT username, email, is_active FROM users;"

# Reset admin password
docker-compose exec soc-api python scripts/reset_password.py admin
```

### Analytics not showing
```bash
# Check Claude API key
echo $ANTHROPIC_API_KEY

# Test analytics endpoint
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:6987/api/analytics?timeRange=24h"

# Check logs for errors
docker-compose logs soc-api | grep -i "analytics\|claude"
```

### SIEM not ingesting
```bash
# Check daemon logs
docker-compose logs soc-daemon | grep -i "siem\|splunk\|azure\|aws\|defender"

# Verify environment variables
docker-compose exec soc-daemon env | grep -i "splunk\|azure\|aws\|defender"

# Test SIEM connection manually
docker-compose exec soc-daemon python -c "
from services.splunk_ingestion import SplunkIngestionService
service = SplunkIngestionService()
print('Splunk connection:', service.test_connection())
"
```

---

## 📞 Getting Help

### Resources
- 📖 **Full Documentation**: See `/docs` folder
- 🧪 **Testing Guide**: See `TESTING_PLAN.md`
- 🚀 **Deployment Guide**: See `PROJECT_COMPLETE.md`
- 🔧 **API Docs**: Visit http://localhost:6987/docs

### Common Issues
- **Login fails**: Check JWT_SECRET_KEY is set
- **No insights**: Verify ANTHROPIC_API_KEY is valid
- **Slow performance**: Check Docker resource limits
- **SIEM not connecting**: Verify credentials and network access

---

## 🎯 Next Steps

### For Development
1. Read `FINAL_IMPLEMENTATION_SUMMARY.md`
2. Review `frontend/PERFORMANCE_OPTIMIZATIONS.md`
3. Check API docs at `/docs`
4. Run `./run_tests.sh --verbose`

### For Production
1. Review security checklist above
2. Set up monitoring (Sentry, DataDog)
3. Configure backups
4. Set up SSL/TLS reverse proxy
5. Deploy to staging first
6. Run full test suite
7. Deploy to production

### For Users
1. Complete user training
2. Review user guides in `/docs`
3. Set up MFA
4. Configure SIEM connections
5. Explore Analytics dashboard
6. Create first case
7. Export to JIRA

---

## ✅ Success Checklist

Quick verification that everything is working:

- [ ] Can access frontend at http://localhost:6988
- [ ] Can login with admin credentials
- [ ] Dashboard shows metrics
- [ ] Can view cases
- [ ] Analytics page loads
- [ ] AI insights generated (Claude 4.5)
- [ ] Charts render correctly
- [ ] Can navigate between pages
- [ ] MFA setup works
- [ ] SIEM data ingesting (if configured)
- [ ] Run `./run_tests.sh` passes

---

## 🎉 You're Ready!

Your AI SOC platform is now running with:
- ✅ User authentication & MFA
- ✅ Role-based access control
- ✅ 4 SIEM integrations
- ✅ AI-powered analytics (Claude 4.5)
- ✅ JIRA integration
- ✅ Optimized performance
- ✅ Comprehensive testing

**Welcome to the future of Security Operations!** 🚀

---

*Last Updated: January 20, 2026*  
*Version: 2.0.0*  
*Status: Production Ready*

