# Phase 06 - MCP Protocol and Registry Plan

## What to do
Define how FAIM will represent MCP-compatible tools, servers, apps, and
capabilities internally.

## Why to do it
The marketplace needs a stable catalog contract before UI or execution can be
expanded. FAIM needs to know what a connector is, what tools it exposes, and
which tenants may install it.

## Where to do it
Likely files:
- `faim_native/api/contracts/`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/schema.sql`
- `faim_native/store/pg/repos/`
- `faim_native/api/routers/`

## Core concepts to define
- MCP server
- MCP app / connector
- tool
- capability
- scope
- installation
- session
- execution request
- execution result
- approval requirement

## Contract rules
- Every catalog item must have stable id, name, version, description, icon,
  auth type, scope requirements, and tool list.
- Every tool must declare input schema, risk level, and execution mode.
- Every installed connector must map back to a tenant and policy state.

## Registry behavior
- Support a built-in FAIM catalog for approved connectors.
- Allow remote discovery only through a safe import path.
- Support versioning so marketplace entries can evolve without breaking older
  installs.

## Safety rules
- Do not trust tool metadata from clients.
- Validate schemas before storing or executing.
- Keep the registry read-only from the browser unless explicitly admin-owned.

