#!/usr/bin/env python3
"""
FAIM-Native: External App Integration Simulation.

This script demonstrates exactly how a 3rd-party developer (AI App, Agent)
integrates with FAIM using API keys and Tenant IDs.
"""

import sys
import os
import asyncio
import base64
import uuid
from typing import Dict, Any

import httpx

# Add package root to path to match internal project imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from store.pg.session import get_session, get_engine
from store.pg.repos.auth_repo import AuthRepo
from store.pg.models_auth import Base

# =============================================================================
# 1. THE DEVELOPER SETUP (Server-Side)
# =============================================================================

def provision_new_tenant(tenant_name: str) -> Dict[str, str]:
    """
    Simulates the FAIM Admin/Portal creating a new tenant and generating a key.
    """
    print(f"--- [PROVISIONING] Creating tenant: {tenant_name} ---")
    
    # Initialize schema
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    session = get_session()
    try:
        repo = AuthRepo(session)
        
        # Create key
        record, plaintext_key = repo.create_tenant_key(tenant_id=tenant_name)
        session.commit()
        
        print(f"SUCCESS: Tenant '{tenant_name}' created.")
        print(f"SECRET: Plaintext Key generated: {plaintext_key}")
        
        return {
            "tenant_id": tenant_name,
            "api_key": plaintext_key
        }
    finally:
        session.close()

# =============================================================================
# 2. THE EXTERNAL PRODUCT (Client-Side)
# =============================================================================

async def simulate_external_request(credentials: Dict[str, str], faim_url: str):
    """
    Simulates a 3rd-party AI Agent or App making a request to FAIM.
    """
    tenant_id = credentials["tenant_id"]
    api_key = credentials["api_key"]
    graph_id = "agent_memory_v1"
    
    print(f"\n--- [CLIENT] Agent App '{tenant_id}' connecting to FAIM ---")
    
    headers = {
        "X-Tenant-Id": tenant_id,
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Step A: Check Health
        print("A. Checking health (Auth Exempt)...")
        try:
            resp = await client.get(f"{faim_url}/health")
            print(f"   Status: {resp.status_code}")
        except Exception as e:
            print(f"   Health check failed: {e}")
            return

        # Step B: Secure Ingest
        print("\nB. Authenticated Ingest (Sending Memory Packet via JSON)...")
        content = "The user preferred dark mode and coffee over tea."
        content_base64 = base64.b64encode(content.encode()).decode()
        
        ingest_data = {
            "graph_id": graph_id,
            "filename": "preferences.txt",
            "bytes_base64": content_base64,
            "profile": "strict"
        }
        
        # CORRECT PATH: /v1/ingest
        resp = await client.post(
            f"{faim_url}/v1/ingest",
            headers=headers,
            json=ingest_data
        )
        
        if resp.status_code == 200:
            print(f"   SUCCESS: Memory ingested for tenant {tenant_id}")
            print(f"   Trace ID: {resp.json().get('request_id', 'unknown')}")
            print(f"   Packet Hash: {resp.json().get('packet_hash')}")
        else:
            print(f"   FAILED: {resp.status_code} - {resp.text}")

        # Step C: Malicious Attack
        print("\nC. Security Test: Attempting access with WRONG key...")
        bad_headers = headers.copy()
        bad_headers["X-Api-Key"] = "faim_bad_key_123456"
        
        resp = await client.post(
            f"{faim_url}/v1/ingest",
            headers=bad_headers,
            json=ingest_data
        )
        print(f"   Result: {resp.status_code} (Rejection expected: 401)")
        if resp.status_code == 401:
            print("   SHIELD ACTIVE: Request rejected by FAIM Middleware.")

# =============================================================================
# MAIN
# =============================================================================

async def main():
    # Use localhost if running locally, or environment variable for container
    FAIM_URL = os.getenv("API_URL", "http://localhost:8000")
    TEST_TENANT = f"agent_app_{uuid.uuid4().hex[:6]}"
    
    creds = provision_new_tenant(TEST_TENANT)
    await simulate_external_request(creds, FAIM_URL)

if __name__ == "__main__":
    asyncio.run(main())
