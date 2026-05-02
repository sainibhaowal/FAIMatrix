from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_admin_ui_and_proxy_routes_exist():
    assert (ROOT / "frontend/src/app/(app)/dashboard/admin/page.tsx").exists()
    assert (ROOT / "frontend/src/app/api/admin/[...path]/route.ts").exists()


def test_admin_auth_and_nav_wiring_is_present():
    auth = (ROOT / "frontend/src/lib/auth.ts").read_text()
    middleware = (ROOT / "frontend/src/middleware.ts").read_text()
    sidebar = (ROOT / "frontend/src/components/layout/Sidebar/SidebarNav.tsx").read_text()
    palette = (ROOT / "frontend/src/components/layout/CommandPalette.tsx").read_text()
    profile_menu = (ROOT / "frontend/src/components/layout/ProfileMenu.tsx").read_text()
    user_dropdown = (
        ROOT / "frontend/src/components/layout/TopBar/ProfileMenu/UserDropdownContent.tsx"
    ).read_text()

    assert "isAdmin" in auth
    assert "/dashboard/admin" in middleware
    assert "/api/admin/" in middleware
    assert "/dashboard/admin" in sidebar
    assert "Open Admin" in palette
    assert "Alerts" in sidebar
    assert "Admin Alerts" in user_dropdown
    assert "/dashboard/admin#alerts" in profile_menu
