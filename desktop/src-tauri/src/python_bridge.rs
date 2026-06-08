//! Python bridge module for Bitmap Vector Studio desktop application.
//!
//! Provides wrappers to invoke the Python CLI (`vector-studio`) and manage
//! the lifecycle of the Python API server process.

use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};

/// Information about the detected Python environment.
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PythonEnvInfo {
    /// Python interpreter version string (e.g. "3.11.4").
    pub python_version: String,
    /// Whether the `vector-studio` CLI command is available in PATH.
    pub vector_studio_installed: bool,
    /// Whether API dependencies (uvicorn, fastapi) are installed.
    pub api_dependencies_installed: bool,
    /// Installed vtracer version, if detectable.
    pub vtracer_version: Option<String>,
}

/// Call the `vector-studio` Python CLI with the provided arguments.
///
/// Falls back to `python -m vector_studio.cli` if the standalone
/// `vector-studio` entry point is not found.
///
/// # Arguments
/// * `args` - CLI arguments to pass to `vector-studio`.
///
/// # Returns
/// The captured stdout on success, or an error message on failure.
pub fn call_vector_studio(args: Vec<String>) -> Result<String, String> {
    let mut cmd = Command::new("vector-studio");
    cmd.args(&args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let output = cmd.output().map_err(|e| {
        // Fallback: try python -m vector_studio.cli
        let fallback = Command::new("python")
            .arg("-m")
            .arg("vector_studio.cli")
            .args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output();

        match fallback {
            Ok(out) => {
                if out.status.success() {
                    return String::from_utf8_lossy(&out.stdout).to_string();
                }
                return format!(
                    "vector-studio failed: {} (fallback also failed: {})",
                    e,
                    String::from_utf8_lossy(&out.stderr)
                );
            }
            Err(fb_err) => format!(
                "vector-studio failed: {} (fallback python -m vector_studio.cli failed: {})",
                e, fb_err
            ),
        }
    })?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(format!(
            "vector-studio exited with error: {}",
            String::from_utf8_lossy(&output.stderr)
        ))
    }
}

/// Start the Python API server on the given port.
///
/// Spawns `vector-studio api --port <port>` as a background process.
///
/// # Arguments
/// * `port` - TCP port to bind the API server.
///
/// # Returns
/// The OS process ID (PID) of the spawned server.
pub fn start_api_server(port: u16) -> Result<u32, String> {
    let mut cmd = Command::new("vector-studio");
    cmd.arg("api")
        .arg("--port")
        .arg(port.to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    let child = cmd.spawn().map_err(|e| {
        // Fallback to python -m vector_studio.cli api --port <port>
        let fallback = Command::new("python")
            .arg("-m")
            .arg("vector_studio.cli")
            .arg("api")
            .arg("--port")
            .arg(port.to_string())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn();

        match fallback {
            Ok(c) => return Ok(c.id()),
            Err(fb_err) => Err(format!(
                "Failed to start API server: {} (fallback also failed: {})",
                e, fb_err
            )),
        }
    });

    match child {
        Ok(c) => Ok(c.id()),
        Err(result) => result,
    }
}

/// Stop the API server process by its PID.
///
/// Uses platform-specific process termination commands.
///
/// # Arguments
/// * `pid` - Process ID returned by `start_api_server`.
pub fn stop_api_server(pid: u32) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("taskkill")
            .args(["/F", "/PID", &pid.to_string()])
            .output()
            .map_err(|e| format!("Failed to execute taskkill: {}", e))?;

        if output.status.success() {
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            // taskkill returns an error if the process is already gone,
            // which is acceptable.
            if stderr.contains("not found") || stderr.contains("不存在") {
                Ok(())
            } else {
                Err(format!("taskkill failed: {}", stderr))
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let output = Command::new("kill")
            .arg("-9")
            .arg(pid.to_string())
            .output()
            .map_err(|e| format!("Failed to execute kill: {}", e))?;

        if output.status.success() {
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            if stderr.contains("No such process") {
                Ok(())
            } else {
                Err(format!("kill failed: {}", stderr))
            }
        }
    }
}

/// Check the Python environment and return diagnostic information.
///
/// Attempts to detect Python version, `vector-studio` availability,
/// and whether API dependencies are present.
pub fn check_python_env() -> Result<PythonEnvInfo, String> {
    // 1. Detect Python version
    let python_version = get_python_version()?;

    // 2. Check if vector-studio CLI is available
    let vector_studio_installed = Command::new("vector-studio")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);

    // 3. Check API dependencies by trying to import uvicorn
    let api_dependencies_installed = Command::new("python")
        .arg("-c")
        .arg("import uvicorn, fastapi")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);

    // 4. Try to get vtracer version
    let vtracer_version = get_vtracer_version().ok();

    Ok(PythonEnvInfo {
        python_version,
        vector_studio_installed,
        api_dependencies_installed,
        vtracer_version,
    })
}

/// Helper: query the Python interpreter version.
fn get_python_version() -> Result<String, String> {
    let output = Command::new("python")
        .args(["--version"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("Failed to run python --version: {}", e))?;

    // python --version writes to stderr in some versions
    let text = if output.stdout.is_empty() {
        String::from_utf8_lossy(&output.stderr)
    } else {
        String::from_utf8_lossy(&output.stdout)
    };

    let version = text.trim().to_string();
    if version.is_empty() {
        return Err("Could not determine Python version".to_string());
    }
    Ok(version)
}

/// Helper: query the installed vtracer version.
fn get_vtracer_version() -> Result<String, String> {
    let output = Command::new("python")
        .args(["-c", "import vtracer; print(vtracer.__version__)"])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("Failed to query vtracer version: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}
