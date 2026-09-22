"""
Student Skills Exchange - One-Click Launcher
Starts both the Flask backend and a simple HTTP server for the frontend
"""
import subprocess
import time
import webbrowser
import os
import sys

print("=" * 60)
print("  🎓 Student Skills Exchange - Starting...")
print("=" * 60)

# Check if on Windows
is_windows = sys.platform.startswith('win')

# Start Flask backend
print("\n[1/3] Starting Flask backend...")
backend_path = os.path.join(os.path.dirname(__file__), 'backend', 'app.py')
backend_process = subprocess.Popen(
    ['python', backend_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE if is_windows else 0
)
time.sleep(2)

# Check if Flask started
if backend_process.poll() is not None:
    print("  ✗ Flask failed to start")
    sys.exit(1)
print("  ✓ Flask backend running on http://localhost:5000")

# Start frontend HTTP server
print("\n[2/3] Starting frontend server...")
frontend_path = os.path.join(os.path.dirname(__file__), 'frontend')
frontend_process = subprocess.Popen(
    ['python', '-m', 'http.server', '8080', '--directory', frontend_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE if is_windows else 0
)
time.sleep(1)

if frontend_process.poll() is not None:
    print("  ✗ Frontend server failed to start")
    backend_process.terminate()
    sys.exit(1)
print("  ✓ Frontend server running on http://localhost:8080")

# Open browser
print("\n[3/3] Opening browser...")
time.sleep(1)
webbrowser.open('http://localhost:8080/index.html')
print("  ✓ Browser opened")

print("\n" + "=" * 60)
print("  ✅ Application is running!")
print("=" * 60)
print("\n  Frontend:  http://localhost:8080")
print("  Backend:   http://localhost:5000")
print("\n  Register a new account or log in to get started.")
print("\n  Press Ctrl+C to stop both servers")
print("=" * 60)

# Keep script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping servers...")
    backend_process.terminate()
    frontend_process.terminate()
    print("Servers stopped. Goodbye!")
