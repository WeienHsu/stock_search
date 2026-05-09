import streamlit as st

from src.auth.auth_manager import (
    authenticate, create_session, is_registration_enabled, is_user_admin, register_user, user_exists,
)


def render() -> None:
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("## 📈 Stock Intelligence")
        st.divider()
        tab_login, tab_register = st.tabs(["登入", "註冊新帳號"])

        with tab_login:
            username = st.text_input("用戶名", key="li_user")
            password = st.text_input("密碼", type="password", key="li_pw")
            if st.button("登入", width="stretch", type="primary"):
                if not username or not password:
                    st.error("請輸入用戶名與密碼")
                else:
                    result = authenticate(username, password)
                    if result:
                        st.session_state["user_id"] = result["user_id"]
                        st.session_state["username"] = username.strip()
                        st.session_state["is_admin"] = result["is_admin"]
                        st.session_state["auth_token"] = create_session(result["user_id"])
                        st.session_state["_set_auth_cookie"] = st.session_state["auth_token"]
                        st.rerun()
                    else:
                        st.error("用戶名或密碼錯誤")

        with tab_register:
            reg_open = not user_exists() or is_registration_enabled()
            if not reg_open:
                st.info("註冊功能已關閉，請聯絡管理員")
            else:
                new_user = st.text_input("用戶名", key="reg_user")
                new_pw = st.text_input("密碼（至少 6 字元）", type="password", key="reg_pw")
                confirm_pw = st.text_input("確認密碼", type="password", key="reg_confirm")
                if st.button("建立帳號", width="stretch", type="primary"):
                    if not new_user or not new_pw:
                        st.error("請填寫所有欄位")
                    elif new_pw != confirm_pw:
                        st.error("兩次密碼不一致")
                    else:
                        try:
                            user_id = register_user(new_user, new_pw)
                            st.session_state["user_id"] = user_id
                            st.session_state["username"] = new_user.strip()
                            st.session_state["is_admin"] = is_user_admin(user_id)
                            st.session_state["auth_token"] = create_session(user_id)
                            st.session_state["_set_auth_cookie"] = st.session_state["auth_token"]
                            st.success("帳號建立成功！")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
