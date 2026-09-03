# FAIM Providers User Manual

## Overview
FAIM providers manage external AI/ML services including embedding models, LLM models, and rerankers. This manual explains how to configure and use providers.

## Accessing Providers
Navigate to: `/providers?tab=<tab-name>

## 1. Provider Tabs

The providers page is organized into tabs, each managing a different type of provider:

### 1.1 Navigator Tab
- **Purpose:** Navigation and overview of all provider types
- **Features:**
  - Overview of all provider families
  - Quick access to each tab
  - System status indicators
- **Content:**
  - Navigator overview UI
  - System status indicators

### 1.2 LLM Families Tab
- **Purpose:** Manage Large Language Model providers
- **Families Included:**
  - **OpenAI:** `gpt-4o`, `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo`
  - **Anthropic:** `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`
  - **Google:** `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`
  - **OpenRouter:** `anthropic/claude-3.5-sonnet`, `deepseek/r1`, `meta/llama-3.3-70b`
  - **Groq:** `llama-3.3-70b`, `mixtral-8x7b`, `gemma2-9b`
  - **OpenAI-Compatible:** Custom models at configured URL
  - **LM Studio:** Local model studio
  - **Ollama:** Local model runner

### 1.3 Embedding Families Tab
- **Purpose:** Manage embedding model providers
- **Families Included:**
  - **FAIM Native:** `BAAI/bge-small-en-v1.5`, `BAAI/bge-m3`
  - **OpenAI Embeddings:** `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`

### 1.4 Reranker Tab
- **Purpose:** Manage reranker models
- **Families Included:**
  - **FAIM Native ReRanker V2:** `faim-reranker-v2` (deterministic, internal core)

### 1.5 OCR Tab
- **Purpose:** OCR engine configuration
- **Settings:**
  - `FAIM_OCR_ENABLED` (default: `true`)
  - `FAIM_OCR_ENGINE` (default: `paddleocr_v6`)
  - `FAIM_OCR_FAIL_CLOSED` (default: `false`)
  - `FAIM_OCR_LANGS` (default: `eng`)

## 2. Adding a New Provider

### 2.1 LLM Provider Addition
1. Navigate to ` /providers?tab=llm`
2. Click "Add New Provider" (if available)
3. Fill in:
   - **Provider Name:** Human-readable name
   - **Code:** Unique identifier (e.g., "openai", "anthropic")
   - **Type:** `openai`, `anthropic`, `google`, `custom`, `local`
   - **Default URL:** API endpoint URL
   - **Models:** Comma-separated list of model names
4. Save — provider appears in selection dropdowns

### 2.2 Embedding Provider Addition
1. Navigate to ` /providers?tab=embedding`
2. Click "Add New Provider"
3. Fill in:
   - **Provider Name:** Human-readable name
   - **Code:** Unique identifier
   - **Type:** `local` or `openai`
   - **Default URL:** API endpoint URL
   - **Models:** Comma-separated list
4. Save — provider appears in selection dropdowns

### 2.3 Reranker Provider Addition
1. Navigate to ` /providers?tab=reranker`
2. Click "Add New Provider"
3. Fill in:
   - **Provider Name:** Human-readable name
   - **Code:** Unique identifier
   - **Type:** `local` (only type supported)
   - **Default URL:** Internal core URL
   - **Models:** Single model name
4. Save — provider appears in selection dropdowns

### 2.5 OCR Configuration
1. Navigate to ` /providers?tab=ocr`
2. Configure:
   - **FAIM_OCR_ENABLED:** Toggle on/off
   - **FAIM_OCR_ENGINE:** Select engine (`paddleocr_v6`, `tesseract`)
   - **FAIM_OCR_FAIL_CLOSED:** Fail-closed behavior
   - **FAIM_OCR_LANGS:** Language codes (`eng`, `eng+fra`, etc.)

## 3. Provider Configuration

### 3.1 Provider Properties
Each provider has the following properties:

| Property | Type | Description |
|---|---|---|
| **id** | String | Unique identifier |
| **name** | String | Human-readable name |
| **code** | String | Machine-readable identifier |
| **type** | String | `openai`, `anthropic`, `google`, `custom`, `local` |
| **defaultUrl** | String | API endpoint URL |
| **models** | String[] | Comma-separated model names |
| **createdAt** | Date | When provider was added |
| **lastUsed** | Date | Last time used (updates on use) |
| **status** | String | `active`, `inactive`, `deprecated` |

### 3.2 Provider Lifecycle
1. **Add:** Provider added via UI
2. **Use:** Selected in downstream components
3. **Update:** Properties modified if needed
4. **Deprecate:** Marked as deprecated (not deleted)
5. **Remove:** Removed from UI (data retained)

## 4. Provider Selection in Downstream Components

### 4.1 Chat Cortex Integration
- When sending messages to Cortex, the selected provider is used
- Provider selection persists across sessions
- Fallback to default provider if selected provider unavailable

### 4.2 Embedding Selection
- Embedding models used for:
  - Knowledge graph node embedding
  - Semantic search
  - Cluster analysis
  - Similarity computation

### 4.3 Reranker Selection
- Reranker used to reorder search results
- Improves relevance of retrieved information
- Configurable similarity threshold

## 5. Provider Management

### 5.1 Adding a Provider
1. Navigate to the appropriate tab
2. Click "Add New Provider" button
3. Fill in the form
4. Save
5. Provider appears in selection dropdowns immediately

### 5.2 Editing a Provider
1. Navigate to the provider tab
2. Click on provider to edit
3. Modify properties
4. Save changes
5. Changes propagate immediately

### 5.3 Deactivating a Provider
1. Navigate to the provider tab
2. Click on provider to deactivate
3. Toggle "active" status to `false`
4. Provider marked as deprecated
5. Still retained in system for reference

## 6. Provider Security

### 6.1 API Key Management
- Providers may require API keys
- Keys stored securely in backend
- Never exposed in frontend code
- Rotation supported (generate new key, update usage)

### 6.2 Tenant Isolation
- Providers are tenant-scoped
- Keys only work for associated tenant
- Cross-tenant keys rejected

### 6.3 Rate Limiting
- Per-provider rate limits configurable
- Exceeded requests return 429
- Headers include `X-Rate-Limit-Remaining`
- Configurable via runtime settings

## 6. Provider Troubleshooting

### Common Issues
| Problem | Cause | Fix |
|---|---|---|
| `Provider not appearing` | Not saved or disabled | Save provider, check status |
| `API key rejected` | Invalid key or expired | Generate new key, update config |
| `Model not found` | Model name typo | Check model spelling, list available models |
| `Connection timeout` | URL incorrect or service down | Verify URL, check service status |
| `Rate limit exceeded` | Too many requests | Wait, or configure higher limit |

### Debug Checklist
1. ✅ Provider saved and status `active`
2. ✅ Correct API key configured
3. ✅ Model name matches exactly
4. ✅ URL correct and service reachable
5. ✅ Rate limits not exceeded

## 7. Provider Integration

### 7.1 Backend Integration
- **Provider discovery:** `lib/providerDiscovery.ts`
- **Provider models:** Defined in `faim_native/encoding/embedding_providers.py`
- **Provider validation:** Backend validates provider/config
- **Provider usage:** Called from Cortex, storage, embedding services

### 7.2 Frontend Integration
- **Provider context:** `ProviderContext` manages selection
- **Embedding provider context:** `EmbeddingProviderContext` manages embeddings
- **Reranker usage:** In search and retrieval pipelines
- **OCR configuration:** Settings in `faim_native/perception/extract/ocr_service.py`

### 7.3 Integration Points
| Component | Uses Providers |
|---|---|
| Cortex Chat | LLM provider for responses |
| Embedding Functions | Embedding provider for vectors |
| Search & Retrieval | Reranker for relevance |
| Storage Ingest | OCR provider for text extraction |
| Dashboard Configuration | All provider types |

## 8. Quick Start

### First Time Use:
1. Log in to FAIM frontend
2. Navigate to `/providers`
3. Select each tab: `llm`, `embedding`, `reranker`, `ocr`
4. Add providers as needed using "Add New Provider"
5. Select providers in your workflows
6. Test with a simple query or operation
7. Verify provider appears in use

### Daily Operations:
1. Check provider status periodically
2. Monitor last-used timestamps
3. Add new providers as needed
4. Retire deprecated providers
5. Monitor rate limits
6. Update configs as required

### Adding Your First Provider:
1. Go to `/providers?tab=llm`
2. Click "Add New Provider"
3. Name: "OpenAI"
4. Code: `openai`
5. Type: `openai`
6. Default URL: `https://api.openai.com/v1`
7. Models: `gpt-4o, gpt-4o-mini`
8. Save
9. Select OpenAI in Cortex chat
10. Test with a simple question

## 8. Frequently Asked Questions

### Q: Can I have multiple LLM providers?
A: Yes — you can add multiple LLM providers and select between them.

### Q: Can I have multiple embedding providers?
A: Yes — you can add multiple embedding providers and select between them.

### Q: Can I disable a provider without deleting it?
A: Yes — toggle status to `inactive`/deprecated.

### Q: What happens if my API key expires?
A: Update the provider with a new key, or generate a new provider.

### Q: Can I use local models only?
A: Yes — all type `local` providers (FAIM Native, LM Studio, Ollama, FAIM Reranker V2).

### Q: Can I use the same provider for different purposes?
A: Yes — embedding providers for vectors, LLM providers for chat, reranker for search relevance.

### Q: How do I check which provider is currently selected?
A: The selected provider is shown in the UI header and persists across sessions.

### Q: Can I export/import provider configurations?
A: The system retains provider data in the backend. For migration, contact support.

## 9. Quick Reference Key Terms

| Term | Definition |
|---|---|
| **Provider** | External AI/ML service configuration |
| **Family** | Group of related providers (LLM, Embedding, Reranker, OCR) |
| **Code** | Machine-readable identifier |
| **Model** | Specific AI model within a provider |
| **Type** | Provider category (`openai`, `anthropic`, `local`, etc.) |
| **Default URL** | API endpoint configuration |
| **Status** | `active`, `inactive`, `deprecated` |

## 9. Quick Reference Commands

| Action | Tab | URL |
|---|---|---|
| Add LLM Provider | `llm` | `/providers?tab=llm` |
| Add Embedding Provider | `embedding` | `/providers?tab=embedding` |
| Add Reranker Provider | `reranker` | `/providers?tab=reranker` |
| Add OCR Config | `ocr` | `/providers?tab=ocr` |
| Navigator Overview | `navigator` | `/providers` |

## 9. Quick Reference Key Providers (Built-in)

| Provider | Type | Models |
|---|---|---|
| **FAIM Native Embeddings** | Embedding | `BAAI/bge-small-en-v1.5`, `BAAI/bge-m3` |
| **FAIM Deterministic ReRanker V2** | Reranker | `faim-reranker-v2` |
| **OpenAI API** | LLM | `gpt-4o, gpt-4o-mini, gpt-4, gpt-3.5-turbo` |
| **Anthropic API** | LLM | `claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus` |
| **Google AI** | LLM | `gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp` |

## 10. Integration Notes

### 10.1 Cortex Chat Integration
- LLM provider selected in UI → used for all Cortex responses
- Provider selection persists across sessions
- Fallback to default if selected unavailable

### 10.2 Embedding Integration
- Embedding provider → used for all node/vector embedding
- Affects search, similarity, clustering
- Selection persists across sessions

### 10.3 Reranker Integration
- Reranker → used for search result reordering
- Improves relevance of retrieved information
- Configurable similarity threshold

### 10.4 OCR Integration
- OCR engine → used for document text extraction
- Configurable via `FAIM_OCR_*` runtime settings
- Affects storage ingest pipeline

## 11. Production Considerations

### 11.1 Security
- API keys stored securely, never in frontend code
- Tenant isolation enforced
- Rate limiting per provider
- Key rotation supported

### 11.2 Performance
- Provider selection persists (no re-fetch needed)
- Model loading may have initial delay
- Rate limits configurable
- Caching where applicable

### 11.3 Reliability
- Built-in fallback to default provider
- Graceful degradation if provider unavailable
- Rate limit handling
- Error logging and monitoring

### 11.4 Compliance
- API key rotation supported
- Audit trail of provider usage
- Tenant isolation enforced
- Data privacy maintained

## 11. Quick Reference Checklist

### For New Provider Setup:
- [ ] Navigate to appropriate tab
- [ ] Click "Add New Provider"
- [ ] Fill in all fields (name, code, type, URL, models)
- [ ] Save provider
- [ ] Test selection in downstream component
- [ ] Verify provider appears in use
- [ ] Monitor first few uses for issues

### For Provider Maintenance:
- [ ] Check status periodically (`active`/`inactive`)
- [ ] Monitor last-used timestamps
- [ ] Add new providers as needed
- [ ] Retire deprecated providers
- [ ] Update API keys if expired
- [ ] Monitor rate limits
- [ ] Review provider usage logs

## 11. Quick Reference Commands

| Action | Tab | URL |
|---|---|---|
| Navigate to Navigator | Root | `/providers` |
| Add LLM Provider | `llm` | `/providers?tab=llm` |
| Add Embedding Provider | `embedding` | `/providers?tab=embedding` |
| Add Reranker Provider | `reranker` | `/providers?tab=reranker` |
| Add OCR Config | `ocr` | `/providers?tab=ocr` |
| Switch Tab | Any | Use tab selector |

## 11. Quick Reference Key Bindings

| Key | Action |
|---|---|
| `Esc` | Close any open dialogs |
| `Tab` | Navigate between tab selector and content |
| `Refresh` | Refresh provider list |
| `F5` | Full page refresh |

