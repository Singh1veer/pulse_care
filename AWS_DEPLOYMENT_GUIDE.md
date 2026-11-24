# AWS Deployment Guide for CampusCare (PulseCare)

This repository contains everything needed to deploy CampusCare on AWS.

---

## 1. What to Share for Deployment

If you are handing this project off to a cloud engineer, client, or deployment team, share the following:

1. **Repository Link & Branch:**
   * **URL:** `https://github.com/Singh1veer/pulse_care.git`
   * **Branch:** `main`

2. **Environment Variables Template (`backend/.env`):**
   ```env
   # Deployment Environment (development / production)
   ENVIRONMENT=production
   
   # Database Mode: 'mysql' for AWS RDS or 'sqlite' for local EC2 file
   DB_MODE=sqlite
   DB_HOST=
   DB_PORT=3306
   DB_NAME=campuscare_dev
   DB_USER=campuscare_dev
   DB_PASSWORD=
   DB_SSL_MODE=DISABLED

   # Security & JWT
   JWT_SECRET_KEY=70344834c93318c01c820877be63963b7655596ca46294ea34aaf50f8f4c517a
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440

   # CORS Allowed Origins (Add your AWS domain or EC2 Public IP)
   CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://<YOUR_EC2_PUBLIC_IP>,https://<YOUR_DOMAIN>
   ```

3. **Required Port Openings (AWS EC2 Security Group Inbound Rules):**
   * **Port 80 (HTTP):** Public web traffic (Frontend).
   * **Port 443 (HTTPS):** Secure traffic (SSL / Let's Encrypt).
   * **Port 22 (SSH):** Administrator server access.
   * **Port 8000 (Custom TCP, optional):** Direct backend API debugging (if not proxied via Nginx).

---

## 2. Option A: 1-Command Docker Deployment on AWS EC2 (Recommended)

### Step 1: Launch EC2 Instance
1. Launch an **Ubuntu 24.04 LTS** EC2 instance (`t3.small` or `t3.medium`).
2. Attach a Security Group with ports `22`, `80`, `443`, and `8000` open.

### Step 2: Install Docker on EC2
Connect via SSH and run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Clone Repository & Launch
```bash
git clone https://github.com/Singh1veer/pulse_care.git
cd pulse_care

# Start the full stack (Backend on :8000 + Frontend on :80)
docker-compose up -d --build
```
Your application will be live at `http://<EC2_PUBLIC_IP>`.

---

## 3. Option B: Native EC2 Deployment (Systemd + Nginx)

### Step 1: Install Dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nodejs npm nginx git
```

### Step 2: Set Up Backend Service
```bash
cd /var/www
sudo git clone https://github.com/Singh1veer/pulse_care.git
cd /var/www/pulse_care/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `/etc/systemd/system/pulse_care_backend.service`:
```ini
[Unit]
Description=CampusCare FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/pulse_care/backend
ExecStart=/var/www/pulse_care/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start the backend service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pulse_care_backend
```

### Step 3: Build Frontend
```bash
cd /var/www/pulse_care/Code/frontend
npm install
npm run build
```

### Step 4: Configure Nginx Reverse Proxy
Edit `/etc/nginx/sites-available/default`:
```nginx
server {
    listen 80;
    server_name _;

    root /var/www/pulse_care/Code/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
}
```
Test and restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 4. Production Domain & Free SSL (Certbot)
If you point a domain (e.g. `clinic.yourdomain.com`) to your EC2 Public IP:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d clinic.yourdomain.com
```
This automatically configures HTTPS on port 443 with automatic certificate renewal.
