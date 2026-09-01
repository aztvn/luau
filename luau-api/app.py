import os
import stat
import urllib.request
import platform
import zipfile
import tempfile
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

LUAU_VERSION = "0.640"
BINARY_NAME = "luau-compile"
if platform.system() == "Windows":
    BINARY_NAME += ".exe"

BINARY_PATH = os.path.join(os.path.dirname(__file__), BINARY_NAME)

def download_luau():
    if os.path.exists(BINARY_PATH):
        return
    
    print(f"Downloading Luau v{LUAU_VERSION}...")
    sys_os = platform.system().lower()
    
    if sys_os == "windows":
        url = f"https://github.com/luau-lang/luau/releases/download/{LUAU_VERSION}/luau-windows.zip"
    elif sys_os == "linux":
        url = f"https://github.com/luau-lang/luau/releases/download/{LUAU_VERSION}/luau-ubuntu.zip"
    elif sys_os == "darwin":
        url = f"https://github.com/luau-lang/luau/releases/download/{LUAU_VERSION}/luau-macos.zip"
    else:
        raise Exception(f"Unsupported OS: {sys_os}")

    zip_path = os.path.join(os.path.dirname(__file__), "luau.zip")
    urllib.request.urlretrieve(url, zip_path)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extract(BINARY_NAME, os.path.dirname(__file__))
    
    os.remove(zip_path)
    
    # Make executable on Linux/Mac
    if sys_os != "windows":
        st = os.stat(BINARY_PATH)
        os.chmod(BINARY_PATH, st.st_mode | stat.S_IEXEC)
    
    print("Downloaded luau-compile successfully!")

# Ensure binary exists on startup
try:
    download_luau()
except Exception as e:
    print(f"Failed to download luau-compile: {e}")

@app.route('/compile', methods=['POST', 'OPTIONS'])
def compile_luau():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight_ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    code = request.form.get('code')
    if not code:
        response = jsonify({"success": False, "error": "No code provided"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400
        
    if not os.path.exists(BINARY_PATH):
        response = jsonify({"success": False, "error": "Compiler binary not found on server"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500

    fd, temp_path = tempfile.mkstemp(suffix=".luau")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
            
        cmd = [BINARY_PATH, "text", temp_path, "-O0"]
        process = subprocess.run(cmd, capture_output=True)
        
        import base64
        stdout_b64 = base64.b64encode(process.stdout).decode('utf-8')
        stderr_str = process.stderr.decode('utf-8', errors='replace') if process.returncode != 0 else ""
        
        response = jsonify({
            "success": True,
            "output_b64": stdout_b64,
            "error": stderr_str
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    except Exception as e:
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    finally:
        os.remove(temp_path)

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "running", "compiler_ready": os.path.exists(BINARY_PATH)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port)
