-- =============================================================================
-- Phase K2 / User-Centric Auth Cleanup
-- =============================================================================
-- Version: 0029
-- Description: Remove legacy admin API key table after user-centric auth shift.
--
-- Notes:
--   - Historical migration 0003 remains untouched for checksum integrity.
--   - This forward migration removes the now-unused legacy admin key table.
-- =============================================================================

DROP TABLE IF EXISTS admin_api_keys;
