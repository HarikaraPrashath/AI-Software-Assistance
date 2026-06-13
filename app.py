import sys
import os
import streamlit as st

import requests
import json
import base64
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Software Engineer", layout="wide")
st.title("🤖 AI Software Engineer")
st.markdown("Describe the app you want built. The agent will plan, code, review, and zip it for you.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("zip_bytes"):
            st.download_button(
                label=f"⬇️ Download {msg.get('zip_filename', 'project.zip')}",
                data=msg["zip_bytes"],
                file_name=msg.get("zip_filename", "project.zip"),
                mime="application/zip",
                key=f"dl_{i}"
            )

user_input = st.chat_input("e.g. Build a weather dashboard in Next.js with Tailwind...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.status("🧠 Agent is working...", expanded=True) as status:
            st.write("📝 Planner thinking...")
            try:
                zip_bytes = None
                zip_filename = ""
                
                response = requests.post(f"{BACKEND_URL}/generate", json={"prompt": user_input}, stream=True)
                response.raise_for_status()

                # Stream the execution to show dynamic UI from HTTP chunks
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    node_name = data.get("node_name")
                    
                    if node_name == "error":
                        st.error(f"Backend Error: {data.get('error')}")
                        continue
                        
                    if node_name == "download_ready":
                        zip_filename = data.get("zip_filename")
                        zip_b64 = data.get("zip_bytes_b64")
                        if zip_b64:
                            zip_bytes = base64.b64decode(zip_b64)
                        continue

                    node_state = data.get("node_state", {})

                    if node_name == "planner":
                        st.write("📝 Planner created the blueprint.")
                        plan = node_state.get("plan")
                    elif node_name == "architect":
                        st.write("🏗️ Architect structured the project.")
                    elif node_name == "coder":
                        st.write("💻 Coder is implementing files...")
                    elif node_name == "reviewer":
                        if node_state.get("status") == "NEEDS_FIX":
                            st.write("🔍 Reviewer found issues. Fixing...")
                        else:
                            st.write("✅ Reviewer approved the codebase.")
                    elif node_name == "zipper":
                        st.write("📦 Project zipped successfully.")
                        zip_path = node_state.get("zip_path", "")
                        if not plan and "plan" in node_state:
                            plan = node_state.get("plan")

                status.update(label="✅ Done!", state="complete")

                app_name = plan["name"] if plan and isinstance(plan, dict) else "Generated Project"
                bot_reply = f"✅ **{app_name}** built successfully!"
                
                st.markdown(bot_reply)
                
                # Auto-download the ZIP file immediately
                if zip_bytes:
                    import streamlit.components.v1 as components
                    b64 = base64.b64encode(zip_bytes).decode()
                    js_code = f"""
                        <a id="auto_download" href="data:application/zip;base64,{b64}" download="{zip_filename}"></a>
                        <script>
                            document.getElementById('auto_download').click();
                        </script>
                    """
                    components.html(js_code, height=0)

                # Store in session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": bot_reply,
                    "zip_bytes": zip_bytes,
                    "zip_filename": zip_filename
                })

                if zip_bytes:
                    st.download_button(
                        label=f"⬇️ Download {zip_filename}",
                        data=zip_bytes,
                        file_name=zip_filename,
                        mime="application/zip",
                        key=f"dl_current_{len(st.session_state.messages)}"
                    )

            except Exception as e:
                status.update(label="❌ Error", state="error")
                bot_reply = f"❌ Error: {e}"
                st.error(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})