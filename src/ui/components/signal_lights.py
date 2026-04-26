import streamlit as st


def render_signal_badge(has_signal: bool, strategy_name: str = "Strategy D") -> None:
    if has_signal:
        st.markdown(
            f'<div style="display:inline-block; background:#7DAA92; color:#fff; '
            f'padding:4px 14px; border-radius:20px; font-size:0.9em; font-weight:600">'
            f'▲ {strategy_name} 訊號觸發</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="display:inline-block; background:#EDE9E4; color:#8A8480; '
            f'padding:4px 14px; border-radius:20px; font-size:0.9em">'
            f'— {strategy_name} 無訊號</div>',
            unsafe_allow_html=True,
        )
