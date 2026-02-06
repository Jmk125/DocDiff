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


st.title("DocDiff - Construction Document Diff")
st.write("Configure inputs and run the diff without using the CLI.")

with st.sidebar:
    st.header("Inputs")

    gmp_col, gmp_btn = st.columns([4, 1])
    gmp_path = gmp_col.text_input("GMP folder", value="./input/GMP", key="gmp_path")
    if gmp_btn.button("Browse", key="browse_gmp"):
        st.session_state.gmp_path = pick_directory(gmp_path)

    bid_col, bid_btn = st.columns([4, 1])
    bid_path = bid_col.text_input("BID folder", value="./input/BID", key="bid_path")
    if bid_btn.button("Browse", key="browse_bid"):
        st.session_state.bid_path = pick_directory(bid_path)

    add_col, add_btn = st.columns([4, 1])
    addenda_path = add_col.text_input("ADDENDA folder (optional)", value="./input/ADDENDA", key="addenda_path")
    if add_btn.button("Browse", key="browse_addenda"):
        st.session_state.addenda_path = pick_directory(addenda_path)

    config_col, config_btn = st.columns([4, 1])
    config_path = config_col.text_input("Config YAML", value="./config.yaml", key="config_path")
    if config_btn.button("Browse", key="browse_config"):
        st.session_state.config_path = filedialog.askopenfilename(
            initialdir=os.getcwd(),
            title="Select config.yaml",
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*")],
        ) or config_path

    output_col, output_btn = st.columns([4, 1])
    output_path = output_col.text_input("Output XLSX", value="./output/changes.xlsx", key="output_path")
    if output_btn.button("Browse", key="browse_output"):
        st.session_state.output_path = filedialog.asksaveasfilename(
            initialdir=os.getcwd(),
            title="Select output XLSX",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        ) or output_path

    log_level = st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], index=0)

st.subheader("Run")
if st.button("Run Diff"):
    args = [
        "--gmp", gmp_path,
        "--bid", bid_path,
        "--out", output_path,
        "--config", config_path,
        "--log-level", log_level,
    ]
    if addenda_path:
        args.extend(["--addenda", addenda_path])
    with st.spinner("Running docdiff..."):
        try:
            run(args)
            st.success(f"Finished. Output written to {output_path}")
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
