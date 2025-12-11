# Municipal Flag NFT - AWS Deployment Guide

## Overview

This guide covers migrating the Municipal Flag NFT platform from Railway to AWS.

**Architecture:**
- **Backend**: EC2 or Elastic Beanstalk with Python/FastAPI
- **Database**: Amazon RDS PostgreSQL
- **Frontend**: S3 + CloudFront static hosting
- **Storage**: IPFS (Pinata - external service)

---

## Prerequisites

1. AWS Account with admin access
2. AWS CLI installed and configured
3. Domain name (optional but recommended)
4. Current Railway database connection details

---

## Phase 1: AWS Account Setup

### 1.1 Create IAM User

1. Go to IAM Console
2. Create new user: `municipal-flag-deployer`
3. Attach policies:
   - `AmazonRDSFullAccess`
   - `AmazonEC2FullAccess`
   - `AmazonS3FullAccess`
   - `CloudFrontFullAccess`
   - `AmazonVPCFullAccess`
4. Create access key and save securely

### 1.2 Create VPC (Optional - use default if not needed)

If using custom VPC:
- Create VPC: `10.0.0.0/16`
- Create subnets: public and private in 2+ AZs
- Create Internet Gateway
- Create NAT Gateway for private subnets

---

## Phase 2: Database Setup (RDS PostgreSQL)

### 2.1 Create RDS Instance

**Console Method:**
1. Go to RDS Console
2. Click "Create database"
3. Configuration:
   - Engine: PostgreSQL 15
   - Template: Free tier or Production
   - DB Instance ID: `municipal-flag-db`
   - Master username: `postgres`
   - Master password: (generate strong password)
   - Instance type: `db.t3.micro` (dev) or `db.t3.small` (prod)
   - Storage: 20 GB gp3
   - VPC: Default or custom
   - Public access: No (EC2 will be in same VPC)
   - Security group: Create new `municipal-flag-db-sg`

**CLI Method:**
```bash
aws rds create-db-instance \
    --db-instance-identifier municipal-flag-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username postgres \
    --master-user-password YOUR_STRONG_PASSWORD \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-xxxxxxxx \
    --backup-retention-period 7 \
    --no-publicly-accessible
```

### 2.2 Configure Security Group

Allow inbound PostgreSQL (port 5432) from:
- EC2 security group
- Your IP (temporarily for migration)

### 2.3 Export Railway Database

```bash
# From Railway CLI or dashboard, get connection string
# Format: postgresql://user:password@host:port/database

# Export database
pg_dump -h <railway-host> -p <port> -U postgres -d railway \
    -F c -f railway_backup.dump
```

### 2.4 Import to AWS RDS

```bash
# Get RDS endpoint from AWS console
# Format: municipal-flag-db.xxxxxx.us-east-1.rds.amazonaws.com

# Import database
pg_restore -h <rds-endpoint> -p 5432 -U postgres -d postgres \
    -c --if-exists railway_backup.dump

# Enter password when prompted
```

### 2.5 Connection String

Format for backend:
```
DATABASE_URL=postgresql://postgres:<password>@<rds-endpoint>:5432/postgres
```

---

## Phase 3: Backend Deployment (EC2)

### 3.1 Create EC2 Instance

**Configuration:**
- AMI: Amazon Linux 2023 or Ubuntu 22.04
- Instance type: `t3.micro` (dev) or `t3.small` (prod)
- Key pair: Create new or use existing
- Network: Same VPC as RDS
- Security group: Create `municipal-flag-backend-sg`
  - Inbound: SSH (22), HTTP (80), HTTPS (443), Custom (8000)
- Storage: 20 GB gp3

### 3.2 Security Group Rules

```
Inbound:
- SSH (22): Your IP
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0
- Custom TCP (8000): 0.0.0.0/0

Outbound:
- All traffic: 0.0.0.0/0
```

### 3.3 Connect and Setup

```bash
# Connect to EC2
ssh -i your-key.pem ec2-user@<public-ip>

# Update system
sudo yum update -y  # Amazon Linux
# or
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Python and dependencies
sudo yum install python3.11 python3.11-pip git -y  # Amazon Linux
# or
sudo apt install python3.11 python3.11-venv python3-pip git -y  # Ubuntu

# Install PostgreSQL client (for testing connection)
sudo yum install postgresql15 -y  # Amazon Linux
# or
sudo apt install postgresql-client -y  # Ubuntu
```

### 3.4 Deploy Backend

```bash
# Clone repository
cd /home/ec2-user
git clone <your-repo-url> municipal-flag-nft
cd municipal-flag-nft/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create .env file
nano .env
```

**Environment Variables (.env):**
```env
# Database
DATABASE_URL=postgresql://postgres:<password>@<rds-endpoint>:5432/postgres

# Server
ENVIRONMENT=production
DEBUG=false
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Admin
ADMIN_API_KEY=your-secure-admin-key

# CORS (update with your CloudFront domain)
CORS_ORIGINS=https://your-domain.com,https://dxxxxxx.cloudfront.net

# Blockchain
CONTRACT_ADDRESS=your-contract-address
POLYGON_AMOY_RPC_URL=https://rpc-amoy.polygon.technology

# IPFS / Pinata
PINATA_API_KEY=your-pinata-api-key
PINATA_API_SECRET=your-pinata-api-secret
PINATA_JWT=your-pinata-jwt

# AI Generation
REPLICATE_API_TOKEN=your-replicate-token

# Google Maps
GOOGLE_MAPS_API_KEY=your-google-maps-key
```

### 3.5 Run with Gunicorn

```bash
# Test run
gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Create systemd service
sudo nano /etc/systemd/system/municipal-flag.service
```

**Systemd Service File:**
```ini
[Unit]
Description=Municipal Flag NFT Backend
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/municipal-flag-nft/backend
Environment="PATH=/home/ec2-user/municipal-flag-nft/backend/venv/bin"
EnvironmentFile=/home/ec2-user/municipal-flag-nft/backend/.env
ExecStart=/home/ec2-user/municipal-flag-nft/backend/venv/bin/gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable municipal-flag
sudo systemctl start municipal-flag
sudo systemctl status municipal-flag

# Check logs
sudo journalctl -u municipal-flag -f
```

### 3.6 Setup Nginx (Optional - for HTTPS)

```bash
# Install Nginx
sudo yum install nginx -y  # Amazon Linux
# or
sudo apt install nginx -y  # Ubuntu

# Configure Nginx
sudo nano /etc/nginx/conf.d/municipal-flag.conf
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Install Certbot for SSL (optional)
sudo yum install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.your-domain.com
```

---

## Phase 4: Frontend Deployment (S3 + CloudFront)

### 4.1 Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://municipal-flag-frontend --region us-east-1

# Enable static website hosting
aws s3 website s3://municipal-flag-frontend \
    --index-document index.html \
    --error-document index.html
```

**Bucket Policy (for CloudFront):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontAccess",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::municipal-flag-frontend/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::ACCOUNT_ID:distribution/DISTRIBUTION_ID"
                }
            }
        }
    ]
}
```

### 4.2 Create CloudFront Distribution

**Console Method:**
1. Go to CloudFront Console
2. Create distribution
3. Configuration:
   - Origin domain: `municipal-flag-frontend.s3.us-east-1.amazonaws.com`
   - Origin access: Origin access control (OAC)
   - Default root object: `index.html`
   - Viewer protocol policy: Redirect HTTP to HTTPS
   - Cache policy: CachingOptimized
   - Price class: Use all edge locations (or choose region)

**Error Pages (for SPA routing):**
- 403 -> /index.html (200)
- 404 -> /index.html (200)

### 4.3 Build and Deploy Frontend

```bash
# On your local machine
cd municipal-flag-nft/frontend

# Create .env.production
cat > .env.production << EOF
VITE_API_URL=https://api.your-domain.com/api
VITE_CONTRACT_ADDRESS=your-contract-address
VITE_CHAIN_ID=80002
VITE_CHAIN_NAME=Polygon Amoy Testnet
VITE_RPC_URL=https://rpc-amoy.polygon.technology
VITE_BLOCK_EXPLORER=https://amoy.polygonscan.com
VITE_IPFS_GATEWAY=https://gateway.pinata.cloud/ipfs
EOF

# Build
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://municipal-flag-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
    --distribution-id EXXXXXXXXXX \
    --paths "/*"
```

---

## Phase 5: DNS Configuration (Optional)

### 5.1 Route 53 Setup

If using custom domain:

1. Create hosted zone for your domain
2. Create A record (alias) pointing to CloudFront
3. Create A record for API subdomain pointing to EC2/ALB
4. Request ACM certificate in us-east-1 for CloudFront

---

## Phase 6: Verification

### 6.1 Backend Health Check

```bash
curl https://api.your-domain.com/api/health
# or
curl http://<ec2-public-ip>:8000/api/health
```

Expected: `{"status": "healthy"}`

### 6.2 Database Connection

```bash
# On EC2
psql -h <rds-endpoint> -U postgres -d postgres -c "SELECT COUNT(*) FROM flags;"
```

### 6.3 Frontend Test

Visit your CloudFront URL and verify:
- Page loads
- API calls succeed
- Data displays correctly

---

## Quick Reference

### Important URLs

| Service | Development | Production |
|---------|-------------|------------|
| Backend API | http://localhost:8000/api | https://api.your-domain.com/api |
| Frontend | http://localhost:5173 | https://your-domain.com |
| RDS Endpoint | - | municipal-flag-db.xxx.rds.amazonaws.com |
| CloudFront | - | dxxxxxx.cloudfront.net |

### Environment Variables Summary

**Backend (.env):**
```
DATABASE_URL=postgresql://postgres:password@rds-endpoint:5432/postgres
ADMIN_API_KEY=secure-key
CORS_ORIGINS=https://your-domain.com
CONTRACT_ADDRESS=0x...
PINATA_API_KEY=...
PINATA_API_SECRET=...
PINATA_JWT=...
REPLICATE_API_TOKEN=...
GOOGLE_MAPS_API_KEY=...
```

**Frontend (.env.production):**
```
VITE_API_URL=https://api.your-domain.com/api
VITE_CONTRACT_ADDRESS=0x...
VITE_IPFS_GATEWAY=https://gateway.pinata.cloud/ipfs
```

---

## Troubleshooting

### Backend Won't Start
- Check logs: `sudo journalctl -u municipal-flag -f`
- Verify .env file exists and has correct permissions
- Test database connection manually

### Database Connection Failed
- Verify security group allows EC2 -> RDS on port 5432
- Check RDS is in same VPC as EC2
- Verify credentials in DATABASE_URL

### CORS Errors
- Update CORS_ORIGINS in backend .env
- Restart backend service
- Clear CloudFront cache

### Frontend 404 on Refresh
- Add error page config in CloudFront
- Set both 403 and 404 to redirect to /index.html with 200

---

## Cost Estimate (Monthly)

| Service | Free Tier | Production |
|---------|-----------|------------|
| EC2 t3.micro | Free (12 months) | ~$10/mo |
| RDS t3.micro | Free (12 months) | ~$15/mo |
| S3 | First 5GB free | ~$1/mo |
| CloudFront | First 1TB free | ~$5/mo |
| **Total** | **~$0** | **~$31/mo** |

---

## Maintenance

### Update Backend
```bash
ssh -i key.pem ec2-user@<ip>
cd municipal-flag-nft
git pull
source backend/venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart municipal-flag
```

### Update Frontend
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://municipal-flag-frontend --delete
aws cloudfront create-invalidation --distribution-id EXXXX --paths "/*"
```

### Database Backup
```bash
# Manual backup
pg_dump -h <rds-endpoint> -U postgres -d postgres -F c -f backup_$(date +%Y%m%d).dump
```

---

**Version:** 1.0
**Last Updated:** December 2025
