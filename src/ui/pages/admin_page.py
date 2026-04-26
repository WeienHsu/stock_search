import streamlit as st

from src.auth.auth_manager import (
    delete_user, is_registration_enabled, list_users, set_admin,
    set_registration_enabled,
)
from src.core.current_user import current_user_is_admin
from src.core.finnhub_mode import current_mode
from src.repositories._backends import get_user_backend


def render(user_id: str) -> None:
    if not current_user_is_admin():
        st.error("無管理員權限")
        st.stop()

    st.markdown("## 👑 使用者管理")

    # ── Registration toggle ──
    st.markdown("### 帳號設定")
    reg_enabled = is_registration_enabled()
    new_val = st.toggle("允許新用戶註冊", value=reg_enabled)
    if new_val != reg_enabled:
        set_registration_enabled(new_val)
        st.success("已更新")
        st.rerun()

    st.markdown("---")

    # ── User list ──
    st.markdown("### 用戶列表")
    users = list_users()
    admin_count = sum(1 for u in users if u["is_admin"])

    for u in users:
        col_name, col_role, col_admin, col_del = st.columns([3, 2, 2, 1])
        col_name.markdown(f"**{u['username']}**")
        col_role.markdown("👑 管理員" if u["is_admin"] else "一般用戶")

        is_self = u["user_id"] == user_id

        if u["is_admin"]:
            can_demote = admin_count > 1 and not is_self
            if col_admin.button("取消管理員", key=f"demote_{u['user_id']}", disabled=not can_demote):
                set_admin(u["user_id"], False)
                st.rerun()
        else:
            if col_admin.button("設為管理員", key=f"promote_{u['user_id']}"):
                set_admin(u["user_id"], True)
                st.rerun()

        if col_del.button("移除", key=f"del_{u['user_id']}", disabled=is_self):
            _purge_and_delete(u["user_id"])
            st.success(f"已移除用戶 {u['username']}")
            st.rerun()

    st.markdown("---")

    # ── System info ──
    st.markdown("### 系統資訊")
    st.caption(f"Finnhub 金鑰模式：`{current_mode()}`")


def _purge_and_delete(target_user_id: str) -> None:
    get_user_backend().purge_user(target_user_id)
    delete_user(target_user_id)
