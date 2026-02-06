import streamlit as st

from docdiff.cli import run


st.set_page_config(page_title="DocDiff UI", layout="wide")

st.title("DocDiff - Construction Document Diff")
st.write("Configure inputs and run the diff without using the CLI.")

with st.sidebar:
    st.header("Inputs")
    gmp_path = st.text_input("GMP folder", value="./input/GMP")
    bid_path = st.text_input("BID folder", value="./input/BID")
    addenda_path = st.text_input("ADDENDA folder (optional)", value="./input/ADDENDA")
    config_path = st.text_input("Config YAML", value="./config.yaml")
    output_path = st.text_input("Output XLSX", value="./output/changes.xlsx")
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
- Paths are local to the machine running this app.
"""
)
