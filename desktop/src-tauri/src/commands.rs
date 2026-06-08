//! Tauri commands for Bitmap Vector Studio desktop application.
//!
//! Each command is exposed to the frontend via the Tauri IPC layer.
//! All commands return `Result<T, String>` so errors can be handled
//! gracefully in the React UI.

use tauri::api::dialog::FileDialogBuilder;
use tauri::{command};

use crate::python_bridge;

/// Convert a single image using the Python CLI.
///
/// # Arguments
/// * `input_path` - Absolute path to the source bitmap image.
/// * `options` - JSON string containing conversion options.
///
/// # Returns
/// JSON result string from the Python backend.
#[command]
pub async fn convert_image(input_path: String, options: String) -> Result<String, String> {
    let args = vec![
        "convert".to_string(),
        input_path,
        "--options".to_string(),
        options,
    ];
    python_bridge::call_vector_studio(args)
}

/// Batch convert multiple images with a preset.
///
/// # Arguments
/// * `files` - List of absolute file paths.
/// * `preset` - Preset name to apply.
///
/// # Returns
/// List of output file paths (one per input).
#[command]
pub async fn batch_convert(files: Vec<String>, preset: String) -> Result<Vec<String>, String> {
    let mut args = vec!["batch".to_string(), "--preset".to_string(), preset];
    for f in &files {
        args.push(f.clone());
    }

    let output = python_bridge::call_vector_studio(args)?;
    // The Python CLI is expected to return a JSON array of output paths.
    let paths: Vec<String> =
        serde_json::from_str(&output).map_err(|e| format!("Invalid batch output: {}", e))?;
    Ok(paths)
}

/// Retrieve available conversion presets from the Python backend.
///
/// # Returns
/// JSON string containing preset definitions.
#[command]
pub async fn get_presets() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["presets".to_string(), "--json".to_string()])
}

/// Retrieve conversion history from the Python backend.
///
/// # Returns
/// JSON string containing history entries.
#[command]
pub async fn get_history() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["history".to_string(), "--json".to_string()])
}

/// Open a native file dialog for selecting images.
///
/// # Returns
/// List of selected file paths, or empty list if cancelled.
#[command]
pub async fn open_file_dialog() -> Result<Vec<String>, String> {
    // Because FileDialogBuilder is synchronous and runs on the main thread,
    // we use tokio::task::spawn_blocking to avoid blocking the async runtime.
    let paths = tokio::task::spawn_blocking(|| {
        let (tx, rx) = std::sync::mpsc::channel();
        FileDialogBuilder::new()
            .add_filter("Images", &["png", "jpg", "jpeg", "bmp", "tiff", "webp"])
            .pick_files(move |file_paths| {
                let result = file_paths
                    .unwrap_or_default()
                    .into_iter()
                    .map(|p| p.to_string_lossy().to_string())
                    .collect::<Vec<String>>();
                let _ = tx.send(result);
            });
        rx.recv().unwrap_or_default()
    })
    .await
    .map_err(|e| format!("File dialog task failed: {}", e))?;

    Ok(paths)
}

/// Open the output folder in the system file manager.
///
/// Uses platform-specific commands (`explorer` on Windows, `open` on macOS,
/// `xdg-open` on Linux) to avoid the ShellScope requirement of Tauri's
/// `shell::open` API.
///
/// # Arguments
/// * `path` - Directory path to open.
#[command]
pub async fn open_output_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
    }

    Ok(())
}

/// Start the Python API server on the requested port.
///
/// # Arguments
/// * `port` - TCP port for the API server.
///
/// # Returns
/// PID of the spawned API server process.
#[command]
pub async fn start_api(port: u16) -> Result<u32, String> {
    python_bridge::start_api_server(port)
}

/// Stop the Python API server by PID.
///
/// # Arguments
/// * `pid` - Process ID returned by `start_api`.
#[command]
pub async fn stop_api(pid: u32) -> Result<(), String> {
    python_bridge::stop_api_server(pid)
}

/// Check the Python environment and return a status summary.
///
/// # Returns
/// Human-readable status string for display in the UI.
#[command]
pub async fn check_env() -> Result<String, String> {
    match python_bridge::check_python_env() {
        Ok(info) => {
            let status = if info.vector_studio_installed && info.api_dependencies_installed {
                "ready"
            } else if info.vector_studio_installed {
                "partial"
            } else {
                "missing"
            };

            let mut msg = format!(
                "Python: {} | vector-studio: {} | API deps: {} | Status: {}",
                info.python_version,
                if info.vector_studio_installed { "OK" } else { "missing" },
                if info.api_dependencies_installed { "OK" } else { "missing" },
                status
            );

            if let Some(v) = info.vtracer_version {
                msg.push_str(&format!(" | vtracer: {}", v));
            }

            Ok(msg)
        }
        Err(e) => Err(format!("Environment check failed: {}", e)),
    }
}
