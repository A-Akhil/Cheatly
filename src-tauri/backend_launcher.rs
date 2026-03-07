// Responsible for launching and monitoring the embedded Python backend process.
//
// Responsibilities:
// - Locate the bundled Python runtime inside the Tauri resource directory
// - Construct the command to run: runtime/python backend/main.py
// - Spawn the backend as a child process using std::process::Command
// - Wait until the backend's /health endpoint responds before signaling ready
// - Monitor the child process and restart it automatically if it exits unexpectedly
// - Terminate the backend child process cleanly when the Tauri app is closing
// - Log backend stdout and stderr to the application log directory
