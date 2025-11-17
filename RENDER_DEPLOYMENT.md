# Render Deployment Guide for KSASUS CSV Visualizer

## Prerequisites
- GitHub account with your code pushed
- Render account (free tier available at https://render.com)

## Step-by-Step Deployment Instructions

### 1. Sign Up / Log In to Render
1. Go to https://render.com
2. Click "Get Started" or "Sign In"
3. Sign up with GitHub (recommended for easy integration)

### 2. Create a New Web Service
1. Click "New +" button in the top right
2. Select "Web Service"
3. Connect your GitHub repository:
   - If first time: Click "Connect GitHub" and authorize Render
   - Select your repository: `santanu153/KSAUS-CSV-Visualiser`
   - Click "Connect"

### 3. Configure Your Web Service

Fill in the following settings:

**Basic Settings:**
- **Name**: `ksasus-csv-visualizer` (or your preferred name)
- **Region**: Choose closest to you (e.g., Oregon, Frankfurt, Singapore)
- **Branch**: `main`
- **Root Directory**: Leave blank
- **Runtime**: `Python 3`

**Build & Deploy Settings:**
- **Build Command**: `chmod +x build.sh && ./build.sh`
- **Start Command**: `gunicorn run:app`

**Instance Type:**
- Select **Free** (for testing) or **Starter** (for better performance)
  - Free tier: Limited resources, spins down after inactivity
  - Starter: $7/month, always-on, better performance

**Environment Variables:**
Click "Add Environment Variable" and add:
- Key: `RENDER`
- Value: `True`

(Optional) Add more if needed:
- Key: `PYTHON_VERSION`
- Value: `3.13.5`

### 4. Deploy
1. Click "Create Web Service" at the bottom
2. Render will automatically:
   - Clone your repository
   - Install dependencies from requirements.txt
   - Run the build script
   - Start your application with gunicorn

### 5. Monitor Deployment
- Watch the logs in real-time on the Render dashboard
- Deployment takes 2-5 minutes typically
- Look for "Build succeeded" message
- Then "Starting service..." message

### 6. Access Your App
Once deployed, you'll see:
- **Your app URL**: `https://ksasus-csv-visualizer.onrender.com` (or similar)
- Click the URL to open your live application!

## Important Notes

### Free Tier Limitations
- Spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds
- 750 hours/month free (enough for testing)
- Limited RAM (512MB)

### Data Persistence
- **Database**: SQLite file persists on Render's disk
- **Uploads**: Files persist in the uploads/ folder
- Data is retained between deployments
- ⚠️ Data may be lost if you delete and recreate the service

### Custom Domain (Optional)
1. Go to Settings → Custom Domain
2. Add your domain
3. Update DNS records as instructed

### Environment Variables
You can add these in Settings → Environment:
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key` (for sessions)

## Troubleshooting

### Build Fails
Check logs for errors:
- Missing dependencies → Update requirements.txt
- Python version mismatch → Check runtime.txt
- Permission errors → Ensure build.sh is executable

### App Crashes
Common issues:
- Port binding: Render uses PORT environment variable automatically
- Database errors: Check if database file has write permissions
- Import errors: Ensure all dependencies are in requirements.txt

### Slow Performance on Free Tier
- First request after spin-down is slow (cold start)
- Upgrade to Starter plan for always-on service
- Consider using background jobs for heavy processing

## Updating Your App

After making code changes:
1. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push origin main
   ```
2. Render automatically detects the push
3. Auto-deploys the new version
4. No manual steps needed!

### Manual Deploy
If auto-deploy doesn't trigger:
1. Go to your service dashboard
2. Click "Manual Deploy" → "Deploy latest commit"

## Monitoring

### View Logs
- Click "Logs" tab in your service dashboard
- Real-time log streaming
- Filter by severity (info, error, etc.)

### Metrics (Starter plan and above)
- CPU usage
- Memory usage
- Request count
- Response times

## Scaling Up

### Vertical Scaling
Upgrade instance type in Settings:
- Starter: $7/month, 512MB RAM
- Standard: $25/month, 2GB RAM
- Pro: Higher resources available

### Horizontal Scaling
Add more instances (paid plans):
- Settings → Instance Count
- Automatic load balancing

## Security Best Practices

1. **Environment Variables**
   - Never commit secrets to GitHub
   - Use Render's environment variables for sensitive data

2. **HTTPS**
   - Automatically enabled by Render
   - Free SSL certificates

3. **File Uploads**
   - Consider file size limits
   - Validate file types (already implemented)

## Cost Optimization

**Free Tier**: Perfect for testing and demos
**Starter Plan** ($7/month): Recommended for:
- Personal projects
- Small user base
- Always-on availability

**When to upgrade**:
- High traffic (>100 users/day)
- Need faster response times
- Require more RAM for large CSV files

## Alternative: PostgreSQL for Database

For production with multiple instances:
1. Create PostgreSQL database on Render
2. Update app/__init__.py to use PostgreSQL
3. Add psycopg2-binary to requirements.txt
4. Set DATABASE_URL environment variable

## Support & Resources

- Render Documentation: https://render.com/docs
- Community Forum: https://community.render.com
- Status Page: https://status.render.com

## Your Deployment URLs

After deployment, save these:
- **App URL**: https://your-app.onrender.com
- **Dashboard**: https://dashboard.render.com

---

## Quick Deploy Checklist

✅ Code pushed to GitHub
✅ Procfile created
✅ requirements.txt includes gunicorn
✅ build.sh created
✅ Render account created
✅ Web Service configured
✅ Environment variables set
✅ Deploy initiated

**Estimated Time**: 10-15 minutes for first deployment

Good luck with your deployment! 🚀
