# Ansible Deployment Checklist

> **PD2 scope — deferred per pd1_pd2_boundary_statement.md**

**Why This Matters:** Manual deployment is error-prone. Ansible automates the entire process, ensuring consistency and enabling quick recovery from failures. One command deploys everything.

---

## Ansible Setup

### Installation
- [ ] Install Ansible on control machine
- [ ] Create ansible directory in project
- [ ] Create directory structure

---

## Inventory Configuration

- [ ] Create inventory.ini file
- [ ] Define production server(s)
- [ ] Define staging server(s)
- [ ] Set connection variables:
  - ansible_host
  - ansible_user
  - ansible_ssh_private_key_file

### Example Inventory
```ini
[production]
webserver ansible_host=192.168.1.10 ansible_user=ubuntu

[staging]
staging ansible_host=192.168.1.20 ansible_user=ubuntu

[all:vars]
app_dir=/opt/injection-alert-system
python_version=3.10
```

---

## Main Playbook

### System Dependencies
- [ ] Update apt cache
- [ ] Install Python 3
- [ ] Install pip
- [ ] Install Python venv
- [ ] Install Nginx
- [ ] Install PostgreSQL
- [ ] Install ModSecurity

### Application Setup
- [ ] Create application directory
- [ ] Create virtual environment
- [ ] Copy requirements.txt
- [ ] Install Python dependencies
- [ ] Copy application code
- [ ] Copy ML model files
- [ ] Copy environment file (secrets)

### Service Configuration
- [ ] Create systemd service for FastAPI
- [ ] Configure Nginx reverse proxy
- [ ] Enable SSL (optional)
- [ ] Start and enable services

---

## Templates

### Systemd Service Template
- [ ] Create flask-app.service.j2 template
- [ ] Configure working directory
- [ ] Configure environment variables
- [ ] Configure restart policy
- [ ] Configure user/group

### Nginx Configuration Template
- [ ] Create nginx.conf.j2 template
- [ ] Configure reverse proxy to FastAPI
- [ ] Configure static file serving
- [ ] Configure SSL (if applicable)
- [ ] Configure request body size limits

### Environment Template
- [ ] Create env.j2 template
- [ ] Database credentials
- [ ] API keys
- [ ] Secret keys
- [ ] Model paths

---

## Handlers

- [ ] Create handler to restart FastAPI service
- [ ] Create handler to restart Nginx
- [ ] Create handler to restart PostgreSQL

---

## Roles (Optional)

### Common Role
- [ ] Install common packages
- [ ] Configure firewall (UFW)
- [ ] Configure timezone
- [ ] Configure swap (if needed)

### Web Server Role
- [ ] Install Nginx
- [ ] Configure Nginx
- [ ] Install SSL certificates

### Database Role
- [ ] Install PostgreSQL
- [ ] Create database
- [ ] Create user
- [ ] Configure access

### Application Role
- [ ] Deploy application code
- [ ] Deploy model files
- [ ] Configure services

---

## Deployment Commands

### Deploy to Staging
```bash
ansible-playbook ansible/deploy.yml -i ansible/inventory.ini --limit staging --ask-become-pass
```

### Deploy to Production
```bash
ansible-playbook ansible/deploy.yml -i ansible/inventory.ini --limit production --ask-become-pass
```

### Dry Run (Check Mode)
```bash
ansible-playbook ansible/deploy.yml -i ansible/inventory.ini --check
```

---

## Post-Deployment Verification

- [ ] Check service status
- [ ] Check Nginx status
- [ ] Test API health endpoint
- [ ] Test prediction endpoint
- [ ] Check logs for errors
- [ ] Verify database connection

---

## Rollback Strategy

- [ ] Keep previous deployment backup
- [ ] Create rollback playbook
- [ ] Document rollback procedure
- [ ] Test rollback process
