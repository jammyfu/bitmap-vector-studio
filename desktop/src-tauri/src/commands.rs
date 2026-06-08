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
/// Calls `vector-studio trace input_path --output temp.svg [options]`.
///
/// # Arguments
/// * `input_path` - Absolute path to the source bitmap image.
/// * `options` - JSON string containing conversion options.
///
/// # Returns
/// JSON result string from the Python backend containing the output SVG path.
#[command]
pub async fn convert_image(input_path: String, options: String) -> Result<String, String> {
    let args = vec![
        "trace".to_string(),
        input_path,
        "--output".to_string(),
        "temp.svg".to_string(),
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

/// Save a user-defined preset to the Python backend.
///
/// # Arguments
/// * `name` - Preset name.
/// * `options` - JSON string containing preset options.
/// * `description` - Preset description.
#[command]
pub async fn save_preset(name: String, options: String, description: String) -> Result<(), String> {
    let args = vec![
        "presets".to_string(),
        "save".to_string(),
        "--name".to_string(),
        name,
        "--options".to_string(),
        options,
        "--description".to_string(),
        description,
    ];
    python_bridge::call_vector_studio(args).map(|_| ())
}

/// Delete a user-defined preset from the Python backend.
///
/// # Arguments
/// * `name` - Preset name to delete.
#[command]
pub async fn delete_preset(name: String) -> Result<(), String> {
    let args = vec![
        "presets".to_string(),
        "delete".to_string(),
        "--name".to_string(),
        name,
    ];
    python_bridge::call_vector_studio(args).map(|_| ())
}

/// Retrieve conversion history from the Python backend.
///
/// # Arguments
/// * `limit` - Maximum number of history entries to return.
///
/// # Returns
/// JSON string containing history entries.
#[command]
pub async fn get_history(limit: u32) -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "history".to_string(),
        "--json".to_string(),
        "--limit".to_string(),
        limit.to_string(),
    ])
}

/// Recommend a preset for the given image.
///
/// Calls `vector-studio trace input_path --recommend`.
///
/// # Arguments
/// * `input_path` - Absolute path to the source bitmap image.
///
/// # Returns
/// JSON string containing the recommendation result.
#[command]
pub async fn recommend_preset(input_path: String) -> Result<String, String> {
    let args = vec![
        "trace".to_string(),
        input_path,
        "--recommend".to_string(),
    ];
    python_bridge::call_vector_studio(args)
}

/// Open an SVG file with an external editor.
///
/// If `editor` is provided, it is used as the executable path.
/// Otherwise the system default application is used.
///
/// # Arguments
/// * `svg_path` - Path to the SVG file.
/// * `editor` - Optional path to the editor executable.
#[command]
pub async fn open_with_editor(svg_path: String, editor: Option<String>) -> Result<(), String> {
    if let Some(ed) = editor {
        std::process::Command::new(&ed)
            .arg(&svg_path)
            .spawn()
            .map_err(|e| format!("Failed to open editor: {}", e))?;
    } else {
        #[cfg(target_os = "windows")]
        {
            std::process::Command::new("cmd")
                .args(["/C", "start", "", &svg_path])
                .spawn()
                .map_err(|e| format!("Failed to open file: {}", e))?;
        }

        #[cfg(target_os = "macos")]
        {
            std::process::Command::new("open")
                .arg(&svg_path)
                .spawn()
                .map_err(|e| format!("Failed to open file: {}", e))?;
        }

        #[cfg(not(any(target_os = "windows", target_os = "macos")))]
        {
            std::process::Command::new("xdg-open")
                .arg(&svg_path)
                .spawn()
                .map_err(|e| format!("Failed to open file: {}", e))?;
        }
    }

    Ok(())
}

/// Retrieve the list of installed plugins.
///
/// # Returns
/// JSON string containing plugin information.
#[command]
pub async fn get_plugins() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["plugins".to_string(), "--json".to_string()])
}

/// Enable a plugin.
///
/// # Arguments
/// * `name` - Plugin name.
#[command]
pub async fn enable_plugin(name: String) -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "plugins".to_string(),
        "enable".to_string(),
        "--name".to_string(),
        name,
    ])
    .map(|_| ())
}

/// Disable a plugin.
///
/// # Arguments
/// * `name` - Plugin name.
#[command]
pub async fn disable_plugin(name: String) -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "plugins".to_string(),
        "disable".to_string(),
        "--name".to_string(),
        name,
    ])
    .map(|_| ())
}

/// Retrieve the current application configuration.
///
/// # Returns
/// JSON string containing configuration key-value pairs.
#[command]
pub async fn get_config() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["config".to_string(), "--json".to_string()])
}

/// Set a configuration value.
///
/// # Arguments
/// * `key` - Configuration key.
/// * `value` - Configuration value.
#[command]
pub async fn set_config(key: String, value: String) -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "config".to_string(),
        "set".to_string(),
        "--key".to_string(),
        key,
        "--value".to_string(),
        value,
    ])
    .map(|_| ())
}

/// Retrieve the market preset list.
///
/// # Returns
/// JSON string containing available market presets.
#[command]
pub async fn market_list() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["market".to_string(), "list".to_string(), "--json".to_string()])
}

/// Install a preset from the market.
///
/// # Arguments
/// * `id` - Market preset ID.
/// * `name` - Optional local name for the installed preset.
///
/// # Returns
/// JSON result string.
#[command]
pub async fn market_install(id: String, name: Option<String>) -> Result<String, String> {
    let mut args = vec![
        "market".to_string(),
        "install".to_string(),
        "--id".to_string(),
        id,
    ];
    if let Some(n) = name {
        args.push("--name".to_string());
        args.push(n);
    }
    python_bridge::call_vector_studio(args)
}

/// Start the conversion queue.
///
/// # Returns
/// OK on success.
#[command]
pub async fn start_queue() -> Result<(), String> {
    python_bridge::call_vector_studio(vec!["queue".to_string(), "start".to_string()]).map(|_| ())
}

/// Pause the conversion queue.
///
/// # Returns
/// OK on success.
#[command]
pub async fn pause_queue() -> Result<(), String> {
    python_bridge::call_vector_studio(vec!["queue".to_string(), "pause".to_string()]).map(|_| ())
}

/// Cancel all pending and running tasks in the queue.
///
/// # Returns
/// OK on success.
#[command]
pub async fn cancel_queue() -> Result<(), String> {
    python_bridge::call_vector_studio(vec!["queue".to_string(), "cancel".to_string()]).map(|_| ())
}

/// Get the current queue status.
///
/// # Returns
/// JSON string containing queue progress and task states.
#[command]
pub async fn get_queue_status() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["queue".to_string(), "status".to_string(), "--json".to_string()])
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
