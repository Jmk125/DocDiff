import os
import tkinter as tk
from tkinter import filedialog

import streamlit as st

from docdiff.cli import run


st.set_page_config(page_title="DocDiff UI", layout="wide")


def pick_directory(default_path: str) -> str:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    selected = filedialog.askdirectory(initialdir=default_path or os.getcwd())
    root.destroy()
    return selected or default_path


def pick_file(default_path: str, title: str, filetypes) -> str:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    selected = filedialog.askopenfilename(
        initialdir=os.path.dirname(default_path) or os.getcwd(),
        title=title,
        filetypes=filetypes,
    )
    root.destroy()
    return selected or default_path


def pick_save_file(default_path: str, title: str, filetypes) -> str:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    selected = filedialog.asksaveasfilename(
        initialdir=os.path.dirname(default_path) or os.getcwd(),
        title=title,
        defaultextension=".xlsx",
        filetypes=filetypes,
    )
    root.destroy()
    return selected or default_path


DEFAULTS = {
    "gmp_path": "./input/GMP",
    "bid_path": "./input/BID",
    "addenda_path": "./input/ADDENDA",
    "config_path": "./config.yaml",
    "output_path": "./output/changes.xlsx",
}

for key, default in DEFAULTS.items():
    st.session_state.setdefault(key, default)


st.title("DocDiff - Construction Document Diff")
st.write("Configure inputs and run the diff without using the CLI.")


with st.sidebar:
    st.header("Inputs")

    def _browse_gmp() -> None:
        st.session_state["gmp_path"] = pick_directory(st.session_state["gmp_path"])

    def _browse_bid() -> None:
        st.session_state["bid_path"] = pick_directory(st.session_state["bid_path"])

    def _browse_addenda() -> None:
        st.session_state["addenda_path"] = pick_directory(st.session_state["addenda_path"])

    def _browse_config() -> None:
        st.session_state["config_path"] = pick_file(
            st.session_state["config_path"],
            "Select config.yaml",
            [("YAML", "*.yaml *.yml"), ("All files", "*")],
        )

    def _browse_output() -> None:
        st.session_state["output_path"] = pick_save_file(
            st.session_state["output_path"],
            "Select output XLSX",
            [("Excel", "*.xlsx")],
        )

    gmp_col, gmp_btn = st.columns([5, 1])
    gmp_col.text_input("GMP folder", key="gmp_path")
    gmp_btn.button("Browse", key="browse_gmp", on_click=_browse_gmp, use_container_width=True)

    bid_col, bid_btn = st.columns([5, 1])
    bid_col.text_input("BID folder", key="bid_path")
    bid_btn.button("Browse", key="browse_bid", on_click=_browse_bid, use_container_width=True)

    add_col, add_btn = st.columns([5, 1])
    add_col.text_input("ADDENDA folder (optional)", key="addenda_path")
    add_btn.button("Browse", key="browse_addenda", on_click=_browse_addenda, use_container_width=True)

    config_col, config_btn = st.columns([5, 1])
    config_col.text_input("Config YAML", key="config_path")
    config_btn.button("Browse", key="browse_config", on_click=_browse_config, use_container_width=True)

    output_col, output_btn = st.columns([5, 1])
    output_col.text_input("Output XLSX", key="output_path")
    output_btn.button("Browse", key="browse_output", on_click=_browse_output, use_container_width=True)

    log_level = st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], index=0)


st.subheader("Run")
if st.button("Run Diff"):
    args = [
        "--gmp", st.session_state["gmp_path"],
        "--bid", st.session_state["bid_path"],
        "--out", st.session_state["output_path"],
        "--config", st.session_state["config_path"],
        "--log-level", log_level,
    ]
    if st.session_state["addenda_path"]:
        args.extend(["--addenda", st.session_state["addenda_path"]])
    with st.spinner("Running docdiff..."):
        try:
            run(args)
            st.success(f"Finished. Output written to {st.session_state['output_path']}")
        except SystemExit as exc:
            if exc.code:
                st.error(f"Run failed with exit code {exc.code}")
        except Exception as exc:
            st.exception(exc)

st.markdown(
    """
### Notes
- The UI wraps the same CLI logic, so configuration changes in `config.yaml` still apply.
- The PDF search is recursive: any PDFs in subfolders under the selected folder are included.
- Paths are local to the machine running this app.
"""
)
