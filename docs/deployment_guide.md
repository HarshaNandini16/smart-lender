# Deployment Guide: IBM Cloud & Docker

This document explains how to deploy the Smart Lender application to production environments using Docker containers and IBM Cloud Foundry / Code Engine.

## Containerized Deployment (Docker)

1. **Build the Docker Image**:
   ```bash
   docker build -t smart-lender:latest .
   ```

2. **Run the Container Locally**:
   ```bash
   docker run -d -p 5000:5000 --name smart-lender-app smart-lender:latest
   ```

3. **Orchestrate with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```

---

## IBM Cloud Deployment (Code Engine)

IBM Cloud Code Engine allows running containerized applications easily.

### Prerequisites:
- IBM Cloud CLI installed.
- Code Engine plugin installed (`ibmcloud plugin install code-engine`).

### Steps:

1. **Log in to IBM Cloud**:
   ```bash
   ibmcloud login --sso
   ```

2. **Select target Resource Group and Region**:
   ```bash
   ibmcloud target -g Default -r us-south
   ```

3. **Create a Code Engine Project**:
   ```bash
   ibmcloud ce project create --name SmartLenderProject
   ibmcloud ce project select --name SmartLenderProject
   ```

4. **Deploy the application directly from the Git Repository**:
   ```bash
   ibmcloud ce app create --name smart-lender \
     --build-source https://github.com/username/SmartLender.git \
     --env SECRET_KEY=ibm_cloud_production_secret_key_8374 \
     --env DEBUG=False \
     --port 5000
   ```
   IBM Cloud will pull the code, use the Dockerfile to build it, host it in their container registry, and expose a secure HTTPS public URL for evaluation.
