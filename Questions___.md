1) you said I dont need llm for memory query?? how? how it can chat with me ? without llms? 
2) 

DOXWISE PLATFORM
|
|-- 1. Platform Admin: You / Your Company Only
|   |
|   |-- Purpose
|   |   |-- operate the platform
|   |   |-- protect security
|   |   |-- handle support
|   |   |-- manage abuse / billing / compliance
|   |
|   |-- Can See
|   |   |-- user email
|   |   |-- user tenant / workspace
|   |   |-- account status
|   |   |-- role: user/editor/admin
|   |   |-- created date
|   |   |-- last login date
|   |   |-- 2FA enabled/disabled
|   |   |-- usage counts
|   |   |   |-- document count
|   |   |   |-- query count
|   |   |   |-- storage used
|   |   |   |-- provider count
|   |   |-- security/audit events
|   |   |   |-- login
|   |   |   |-- failed login
|   |   |   |-- upload event
|   |   |   |-- delete event
|   |   |   |-- provider added/removed
|   |   |   |-- role changed
|   |
|   |-- Should Not See By Default
|   |   |-- document text/content
|   |   |-- chat/query prompt content
|   |   |-- generated answers
|   |   |-- provider API keys
|   |   |-- OAuth tokens
|   |   |-- local/VPS private endpoint secrets
|   |   |-- raw storage object paths
|   |
|   |-- Can Do
|   |   |-- disable user
|   |   |-- reactivate user
|   |   |-- force logout
|   |   |-- delete user data
|   |   |-- revoke provider connection
|   |   |-- view platform metrics
|   |   |-- view audit logs
|   |   |-- manage billing/plans later
|   |   |-- configure platform/system providers
|   |
|   |-- Break-Glass Access
|   |   |-- only if legally/support/security required
|   |   |-- must require reason
|   |   |-- must create audit log
|   |   |-- should be limited-time
|   |   |-- should never expose secrets
|   |
|   |-- Admin Data Rules
|       |-- metadata first
|       |-- no private content by default
|       |-- no secret values ever
|       |-- every sensitive action audited
|       |-- minimum data needed only
|
|-- 2. Editor: Power User
|   |
|   |-- Purpose
|   |   |-- advanced product features
|   |   |-- heavier usage
|   |   |-- maybe workspace collaboration later
|   |
|   |-- Can See
|   |   |-- own profile
|   |   |-- own documents
|   |   |-- own chats/queries
|   |   |-- own providers
|   |   |-- shared collections they were invited to
|   |   |-- workspace resources only if explicitly shared
|   |
|   |-- Can Do
|   |   |-- upload documents
|   |   |-- query documents
|   |   |-- use advanced tools/features
|   |   |-- create/manage own providers
|   |   |-- create shared collections
|   |   |-- invite users to collections/workspaces if allowed
|   |
|   |-- Cannot Do
|       |-- access admin dashboard
|       |-- see other users' private providers
|       |-- use other users' provider keys
|       |-- see other users' private documents
|       |-- see platform-wide users
|       |-- delete other users' accounts
|
|-- 3. User: Normal Customer
|   |
|   |-- Purpose
|   |   |-- private document AI usage
|   |   |-- own account
|   |
|   |-- Can See
|   |   |-- own profile
|   |   |-- own documents
|   |   |-- own queries/chats
|   |   |-- own providers
|   |   |-- shared collections only when invited/accepted
|   |
|   |-- Can Do
|   |   |-- upload own documents
|   |   |-- query own documents
|   |   |-- delete own documents
|   |   |-- configure own provider
|   |   |-- revoke own provider
|   |
|   |-- Cannot Do
|       |-- access admin dashboard
|       |-- see tenant-wide users
|       |-- see other users' documents
|       |-- see other users' chats
|       |-- see other users' providers
|       |-- use other users' API keys
|
|-- 4. Data Isolation Model
|   |
|   |-- Every Private Object Must Have
|   |   |-- tenant_id
|   |   |-- owner_user_id
|   |   |-- optional workspace_id
|   |
|   |-- Private By Default
|   |   |-- documents
|   |   |-- chunks
|   |   |-- embeddings
|   |   |-- queries
|   |   |-- chats
|   |   |-- providers
|   |   |-- provider secrets
|   |   |-- local/VPS provider endpoints
|   |
|   |-- Shared Only By Explicit Permission
|   |   |-- collection membership
|   |   |-- workspace membership
|   |   |-- workspace provider assignment
|   |   |-- tenant/system provider assignment
|   |
|   |-- Isolation Query Rule
|       |-- user/editor:
|       |   |-- tenant_id = my tenant
|       |   |-- owner_user_id = me
|       |   |-- OR explicit shared permission
|       |
|       |-- admin:
|           |-- metadata access by default
|           |-- content access only break-glass
|
|-- 5. Provider Design
|   |
|   |-- User Provider
|   |   |-- owned by one user
|   |   |-- private API key
|   |   |-- private local/VPS URL
|   |   |-- only owner can test/use/edit/delete
|   |
|   |-- Workspace Provider
|   |   |-- explicitly shared to workspace
|   |   |-- created by admin or workspace owner
|   |   |-- visible as shared provider
|   |   |-- users cannot read key
|   |
|   |-- Platform Provider
|   |   |-- configured by your company
|   |   |-- used as default/fallback
|   |   |-- no customer-owned secret exposed
|   |
|   |-- Provider Secret Rules
|       |-- encrypt always
|       |-- never return real value
|       |-- mask only
|       |-- admin can revoke/rotate
|       |-- admin cannot read
|       |-- runtime can decrypt only for authorized owner/scope
|
|-- 6. Document / Query Privacy
|   |
|   |-- User Owns
|   |   |-- uploaded files
|   |   |-- extracted text
|   |   |-- chunks
|   |   |-- embeddings
|   |   |-- chat history
|   |   |-- query history
|   |
|   |-- Admin Sees By Default
|   |   |-- document count
|   |   |-- storage used
|   |   |-- processing status count
|   |   |-- error count
|   |
|   |-- Admin Does Not See By Default
|       |-- filenames if avoidable
|       |-- file content
|       |-- chunk text
|       |-- prompt text
|       |-- answer text
|
|-- 7. Audit / Compliance
|   |
|   |-- Always Audit
|   |   |-- admin login
|   |   |-- user disable/reactivate/delete
|   |   |-- force logout
|   |   |-- provider revoke/rotate/delete
|   |   |-- data deletion request
|   |   |-- role change
|   |   |-- break-glass access
|   |
|   |-- Audit Details Must Not Store
|   |   |-- API keys
|   |   |-- OAuth tokens
|   |   |-- document content
|   |   |-- prompt content
|   |   |-- full answers
|   |   |-- raw secret-bearing errors
|   |
|   |-- Store Instead
|       |-- actor_user_id
|       |-- target_user_id
|       |-- action
|       |-- resource_type
|       |-- resource_id
|       |-- timestamp
|       |-- reason
|       |-- status
|
|-- 8. Company Needs
|   |
|   |-- Required
|   |   |-- know who uses platform
|   |   |-- user account status
|   |   |-- usage/billing counts
|   |   |-- abuse/security monitoring
|   |   |-- error/debug metadata
|   |   |-- legal deletion/export handling
|   |   |-- support tools
|   |
|   |-- Not Required By Default
|       |-- reading private documents
|       |-- reading private chats
|       |-- seeing provider secrets
|       |-- using customer provider keys
|
|-- 9. User Needs
|   |
|   |-- Required
|   |   |-- private account
|   |   |-- private documents
|   |   |-- private chats
|   |   |-- private providers
|   |   |-- clear delete/export controls
|   |   |-- clear sharing controls
|   |   |-- trust that admin cannot casually inspect content
|   |
|   |-- User Controls
|       |-- upload/delete docs
|       |-- delete account/data
|       |-- revoke provider
|       |-- manage shared collections
|       |-- leave workspace/collection
|
|-- 10. Implementation Plan
    |
    |-- Phase 1: Roles
    |   |-- keep user/editor/admin
    |   |-- admin = internal platform staff only
    |   |-- remove provider-wide powers from user/editor unless owner-scoped
    |
    |-- Phase 2: Ownership Columns
    |   |-- provider_configs.owner_user_id
    |   |-- provider_assignments.owner_user_id
    |   |-- maybe conversations/documents already have owner fields
    |
    |-- Phase 3: API Filtering
    |   |-- list only own private data
    |   |-- include shared only through permissions
    |   |-- admin metadata-only endpoints
    |
    |-- Phase 4: Provider Runtime Isolation
    |   |-- resolve providers by owner_user_id
    |   |-- never fallback to another user's provider
    |   |-- local/VPS provider only owner can use
    |
    |-- Phase 5: Admin Privacy
    |   |-- admin users page = metadata/counts
    |   |-- admin tenants page = counts
    |   |-- admin audit logs = redacted details
    |   |-- admin documents = counts/status only
    |
    |-- Phase 6: Break-Glass
    |   |-- separate endpoint
    |   |-- requires reason
    |   |-- audited
    |   |-- no secrets
    |
    |-- Phase 7: Tests
        |-- user A cannot see user B documents
        |-- user A cannot see/use user B providers
        |-- editor cannot access admin
        |-- admin cannot read secrets
        |-- admin sensitive actions audited
        |-- audit logs redact secrets/content
nowe