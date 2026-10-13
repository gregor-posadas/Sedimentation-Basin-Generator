"""Sedimentation basin design for CE 323 (Streamlit app entry point)."""
import streamlit as st

st.set_page_config(
    page_title="Sedimentation Basin Design · CE 323",
    page_icon=":material/water:",
    layout="wide",
    initial_sidebar_state="auto",
)


def _refresh_local_modules(names, stamp_only=False):
    """Streamlit Community Cloud can keep running an old copy of a module after a new commit is pulled.
    Reload any of this app's modules whose file has changed since it was loaded, and everything listed after
    it (they may hold references to the old one)."""
    import importlib
    import os
    import sys
    changed = False
    for name in names:
        m = sys.modules.get(name)
        if m is None:
            continue
        try:
            mt = os.path.getmtime(m.__file__)
        except (OSError, TypeError):
            continue
        if stamp_only:
            if getattr(m, "_loaded_mtime", None) is None:
                m._loaded_mtime = mt
            continue
        if changed or getattr(m, "_loaded_mtime", None) != mt:
            importlib.reload(m)
            m._loaded_mtime = mt
            changed = True


_refresh_local_modules(["explainers", "ui_theme", "basin_calc", "basin_anim", "pages_basin"])
import pages_basin  # noqa: E402  (after set_page_config)
_refresh_local_modules(["explainers", "ui_theme", "basin_calc", "basin_anim", "pages_basin"], stamp_only=True)

st.navigation(
    [
        st.Page(pages_basin.tool_page, title="Basin design", icon=":material/straighten:", default=True),
        st.Page(pages_basin.accessibility_page, title="Accessibility", icon=":material/accessibility_new:",
                url_path="accessibility"),
    ]
).run()
