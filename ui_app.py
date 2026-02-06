import io
import json
import logging
import os
import tkinter as tk
from tkinter import filedialog

import httpx
from openai import OpenAI
import streamlit as st

from docdiff.ai import AiConfig, ai_scan_matches
from docdiff.cli import build_results, load_config
from docdiff.export_excel import write_workbook


st.set_page_config(page_title="DocDiff UI", layout="wide")


def make_openai_client(api_key: str | None) -> OpenAI:
    return OpenAI(
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
        http_client=httpx.Client(trust_env=False),
    )


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
    "results_ready": False,
    "changes": [],
    "inventory": [],
    "matches": [],
    "log_output": "",
    "ai_reviews": {},
    "ai_findings": [],
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
    sets = {
        "GMP": st.session_state["gmp_path"],
        "BID": st.session_state["bid_path"],
    }
    if st.session_state["addenda_path"]:
        sets["ADDENDA"] = st.session_state["addenda_path"]
    with st.spinner("Running docdiff..."):
        try:
            handler = logging.StreamHandler(stream=io.StringIO())
            formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
            handler.setFormatter(formatter)
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            root_logger.setLevel(getattr(logging, log_level, logging.INFO))

            config = load_config(st.session_state["config_path"])
            changes, inventory, matches = build_results(config, sets)

            handler.flush()
            log_stream = handler.stream.getvalue()
            root_logger.removeHandler(handler)

            st.session_state["changes"] = changes
            st.session_state["inventory"] = inventory
            st.session_state["matches"] = matches
            st.session_state["log_output"] = log_stream
            st.session_state["results_ready"] = True
            st.session_state["ai_reviews"] = {}
            st.session_state["ai_findings"] = []

            st.success("Finished processing. Review results below or export to Excel.")
        except SystemExit as exc:
            if exc.code:
                st.error(f"Run failed with exit code {exc.code}")
        except Exception as exc:
            st.exception(exc)

st.subheader("Console Output")
st.text_area("Logs", value=st.session_state.get("log_output", ""), height=200)

if st.session_state.get("results_ready"):
    st.subheader("Preview Results")
    st.write(
        f"Changes: {len(st.session_state['changes'])} | "
        f"Inventory: {len(st.session_state['inventory'])} | "
        f"Matches: {len(st.session_state['matches'])}"
    )

    change_rows = [
        {
            "Change_ID": row.change_id,
            "Set_From": row.set_from,
            "Set_To": row.set_to,
            "Discipline": row.discipline,
            "Doc_Type": row.doc_type,
            "Reference": row.reference,
            "Change_Type": row.change_type,
            "Change_Summary": row.change_summary,
            "Confidence": row.confidence,
            "Impact_Score": row.impact_score,
            "Impact_Rationale": row.impact_rationale,
            "AI_Significance_1to5": st.session_state.get("ai_reviews", {}).get(row.change_id, {}).get("score", ""),
            "AI_Rationale": st.session_state.get("ai_reviews", {}).get(row.change_id, {}).get("rationale", ""),
        }
        for row in st.session_state["changes"]
    ]
    st.dataframe(change_rows, use_container_width=True, height=400)

    st.subheader("AI Review (optional)")
    st.write("Generate AI-based significance scores and rationale before exporting.")
    api_key = st.text_input(
        "OpenAI API Key (optional, otherwise uses OPENAI_API_KEY env var)",
        type="password",
    )
    model_name = st.text_input("Model", value="gpt-4o-mini")
    max_items = st.number_input("Max changes to review", min_value=1, max_value=200, value=50, step=1)

    def _ai_review_row(row) -> dict:
        client = make_openai_client(api_key)
        prompt = (
            "You are an estimator assistant. Rate significance 1-5 and give a short rationale. "
            "Respond as JSON with keys score (int 1-5) and rationale (string).\n\n"
            f"Discipline: {row.discipline}\n"
            f"Doc Type: {row.doc_type}\n"
            f"Reference: {row.reference}\n"
            f"Change Type: {row.change_type}\n"
            f"Summary: {row.change_summary}\n"
            f"Before: {row.before_snippet[:500]}\n"
            f"After: {row.after_snippet[:500]}\n"
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    if st.button("Run AI Review"):
        if not (api_key or os.getenv("OPENAI_API_KEY")):
            st.error("No API key provided. Set OPENAI_API_KEY or paste a key above.")
        else:
            with st.spinner("Running AI review..."):
                sorted_changes = sorted(
                    st.session_state["changes"],
                    key=lambda c: (-c.impact_score, c.discipline, c.reference),
                )
                ai_results = {}
                for row in sorted_changes[:max_items]:
                    try:
                        result = _ai_review_row(row)
                        ai_results[row.change_id] = {
                            "score": result.get("score", ""),
                            "rationale": result.get("rationale", ""),
                        }
                    except Exception as exc:
                        ai_results[row.change_id] = {"score": "", "rationale": f"AI error: {exc}"}
                st.session_state["ai_reviews"] = ai_results
                st.success("AI review complete. Preview table updated.")

    st.subheader("AI Scan (include in diff)")
    st.write("Run AI comparison across matched pages and append findings to the change list.")
    scan_enabled = st.checkbox("Enable AI scan", value=False)
    scan_model = st.text_input("AI scan model", value="gpt-4o-mini")
    scan_max_pages = st.number_input("Max pages to scan", min_value=1, max_value=1000, value=200, step=10)
    scan_max_chars = st.number_input("Max chars per page", min_value=500, max_value=6000, value=2000, step=250)

    if st.button("Run AI Scan"):
        if not scan_enabled:
            st.warning("Enable AI scan to proceed.")
        elif not (api_key or os.getenv("OPENAI_API_KEY")):
            st.error("No API key provided. Set OPENAI_API_KEY or paste a key above.")
        else:
            with st.spinner("Running AI scan across documents..."):
                client = make_openai_client(api_key)
                ai_config = AiConfig(
                    model=scan_model,
                    max_items=int(scan_max_pages),
                    max_chars=int(scan_max_chars),
                )
                ai_findings = ai_scan_matches(client, st.session_state["matches"], ai_config)
                st.session_state["ai_findings"] = ai_findings
                st.session_state["changes"] = st.session_state["changes"] + ai_findings
                st.success(f"AI scan added {len(ai_findings)} findings to the change list.")

    if st.button("Export to Excel"):
        try:
            write_workbook(
                st.session_state["output_path"],
                st.session_state["changes"],
                st.session_state["inventory"],
                st.session_state["matches"],
            )
            st.success(f"Exported to {st.session_state['output_path']}")
        except Exception as exc:
            st.exception(exc)

st.markdown(
    """
### Notes
- The UI wraps the same CLI logic, so configuration changes in `config.yaml` still apply.
- The PDF search is recursive: any PDFs in subfolders under the selected folder are included.
- Paths are local to the machine running this app.
- Results are held in memory for preview; export writes the Excel file on demand.
- AI review is optional and uses the OpenAI API if a key is provided.
"""
)
