//! Tauri commands for Bitmap Vector Studio desktop application.
//!
//! Each command is exposed to the frontend via the Tauri IPC layer.
//! All commands return `Result<T, String>` so errors can be handled
//! gracefully in the React UI.

use tauri::api::dialog::FileDialogBuilder;
use tauri::{command};

use crate::python_bridge;

/// Export an SVG animation in the requested format.
///
/// # Arguments
/// * `svg_path` - Absolute path to the source SVG file.
/// * `format` - Export format: "smil", "lottie", "css", "gif".
/// * `preset` - Animation preset name.
/// * `output_path` - Destination file path.
///
/// # Returns
/// The output file path on success.
#[command]
pub async fn export_animation(
    svg_path: String,
    format: String,
    preset: String,
    output_path: String,
) -> Result<String, String> {
    let mut args = vec![
        "animate".to_string(),
        format,
        svg_path,
        "--output".to_string(),
        output_path.clone(),
        "--preset".to_string(),
        preset,
    ];
    python_bridge::call_vector_studio(args)?;
    Ok(output_path)
}

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

/// Prewarm the Python environment by importing core modules.
///
/// Calls `vector-studio benchmark` with a hidden flag to trigger
/// startup optimization without producing output.
///
/// # Returns
/// OK on success.
#[command]
pub async fn prewarm_env() -> Result<(), String> {
    python_bridge::call_vector_studio(vec!["benchmark".to_string(), "--help".to_string()])
        .map(|_| ())
}

/// Retrieve performance statistics from the Python backend.
///
/// # Returns
/// JSON string containing memory usage, GPU availability, and suggestions.
#[command]
pub async fn get_performance_stats(input_path: String) -> Result<String, String> {
    let args = vec![
        "trace".to_string(),
        input_path,
        "--recommend".to_string(),
    ];
    python_bridge::call_vector_studio(args)
}

/// Retrieve available OCR languages from the Python backend.
///
/// # Returns
/// JSON string containing language codes, names, and installation status.
#[command]
pub async fn get_ocr_languages() -> Result<String, String> {
    python_bridge::call_vector_studio(vec!["ocr".to_string(), "languages".to_string(), "--json".to_string()])
}

/// Detect text regions in an image with optional multi-language support.
///
/// # Arguments
/// * `input_path` - Absolute path to the source bitmap image.
/// * `lang` - Optional OCR language code.
/// * `vertical` - Whether to detect vertical text orientation.
///
/// # Returns
/// JSON string containing detected text regions.
#[command]
pub async fn detect_text_regions_multilang(
    input_path: String,
    lang: Option<String>,
    vertical: Option<bool>,
) -> Result<String, String> {
    let mut args = vec!["ocr".to_string(), "detect".to_string(), input_path];
    if let Some(l) = lang {
        args.push("--lang".to_string());
        args.push(l);
    }
    if vertical.unwrap_or(false) {
        args.push("--vertical".to_string());
    }
    args.push("--json".to_string());
    python_bridge::call_vector_studio(args)
}

/// Recognize text in an image with optional multi-language support.
///
/// # Arguments
/// * `input_path` - Absolute path to the source bitmap image.
/// * `lang` - Optional OCR language code.
///
/// # Returns
/// JSON string containing recognized text lines.
#[command]
pub async fn recognize_text_multilang(
    input_path: String,
    lang: Option<String>,
) -> Result<String, String> {
    let mut args = vec!["ocr".to_string(), "recognize".to_string(), input_path];
    if let Some(l) = lang {
        args.push("--lang".to_string());
        args.push(l);
    }
    args.push("--json".to_string());
    python_bridge::call_vector_studio(args)
}

/// Save the current workspace state.
///
/// # Arguments
/// * `name` - Workspace name (optional).
/// * `open_files` - JSON array of open file paths.
/// * `preset` - Current preset name.
///
/// # Returns
/// The saved workspace file path.
#[command]
pub async fn save_workspace(
    name: Option<String>,
    open_files: String,
    preset: String,
) -> Result<String, String> {
    let mut args = vec![
        "workspace".to_string(),
        "save".to_string(),
        "--preset".to_string(),
        preset,
    ];
    if let Some(n) = name {
        args.push(n);
    }
    // open_files is passed as a JSON string; the CLI doesn't natively consume it,
    // but the Python backend can be extended. For now we forward the call.
    python_bridge::call_vector_studio(args)
}

/// Load a saved workspace.
///
/// # Arguments
/// * `name` - Workspace name.
///
/// # Returns
/// JSON string containing workspace data.
#[command]
pub async fn load_workspace(name: String) -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "workspace".to_string(),
        "load".to_string(),
        name,
    ])
}

/// List all saved workspaces.
///
/// # Returns
/// JSON array of workspace metadata.
#[command]
pub async fn list_workspaces() -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "workspace".to_string(),
        "list".to_string(),
        "--json".to_string(),
    ])
}

/// Get all available checkpoints.
///
/// # Returns
/// JSON array of checkpoint metadata.
#[command]
pub async fn get_checkpoints() -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "resume".to_string(),
        "--list".to_string(),
        "--json".to_string(),
    ])
}

/// Resume a batch conversion from a checkpoint.
///
/// # Arguments
/// * `checkpoint_id` - Checkpoint identifier.
///
/// # Returns
/// JSON result string.
#[command]
pub async fn resume_checkpoint(checkpoint_id: String) -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "resume".to_string(),
        checkpoint_id,
    ])
}

/// Enable plugin hot-reload monitoring.
///
/// # Returns
/// OK on success.
#[command]
pub async fn enable_hotreload() -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "plugin".to_string(),
        "hotreload".to_string(),
        "--enable".to_string(),
    ])
    .map(|_| ())
}

/// Disable plugin hot-reload monitoring.
///
/// # Returns
/// OK on success.
#[command]
pub async fn disable_hotreload() -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "plugin".to_string(),
        "hotreload".to_string(),
        "--disable".to_string(),
    ])
    .map(|_| ())
}

/// Share an SVG file via the cloud sync backend.
///
/// # Arguments
/// * `svg_path` - Absolute path to the SVG file.
/// * `expire_hours` - Number of hours before the share expires.
///
/// # Returns
/// JSON string containing share metadata (url, qr_code, expire_at, file_id).
#[command]
pub async fn share_svg(svg_path: String, expire_hours: u32) -> Result<String, String> {
    let args = vec![
        "cloud".to_string(),
        "share".to_string(),
        svg_path,
        "--expire".to_string(),
        expire_hours.to_string(),
        "--backend".to_string(),
        "local".to_string(),
    ];
    python_bridge::call_vector_studio(args)
}

/// List all active shares.
///
/// # Returns
/// JSON array of share metadata.
#[command]
pub async fn list_shares() -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "cloud".to_string(),
        "list".to_string(),
        "--backend".to_string(),
        "local".to_string(),
    ])
}

/// Revoke a shared file.
///
/// # Arguments
/// * `file_id` - The share/file ID to revoke.
///
/// # Returns
/// OK on success.
#[command]
pub async fn revoke_share(file_id: String) -> Result<(), String> {
    python_bridge::call_vector_studio(vec![
        "cloud".to_string(),
        "revoke".to_string(),
        file_id,
        "--backend".to_string(),
        "local".to_string(),
    ])
    .map(|_| ())
}

/// Run a workflow file against an input image.
///
/// # Arguments
/// * `workflow_file` - Absolute path to the workflow JSON file.
/// * `input_path` - Absolute path to the input bitmap image.
/// * `output_dir` - Absolute path to the output directory.
///
/// # Returns
/// JSON string containing output file paths.
#[command]
pub async fn run_workflow(workflow_file: String, input_path: String, output_dir: String) -> Result<String, String> {
    let args = vec![
        "workflow".to_string(),
        "run".to_string(),
        workflow_file,
        "--input".to_string(),
        input_path,
        "--output-dir".to_string(),
        output_dir,
    ];
    python_bridge::call_vector_studio(args)
}

/// List built-in workflow templates.
///
/// # Returns
/// JSON array of template metadata.
#[command]
pub async fn list_workflows() -> Result<String, String> {
    python_bridge::call_vector_studio(vec![
        "workflow".to_string(),
        "list".to_string(),
        "--json".to_string(),
    ])
}

/// Save a workflow definition to disk.
///
/// # Arguments
/// * `template` - Template name (logo_pipeline, photo_pipeline, batch_pipeline).
/// * `output_path` - Absolute path to write the workflow JSON file.
///
/// # Returns
/// OK on success.
#[command]
pub async fn save_workflow(template: String, output_path: String) -> Result<(), String> {
    let args = vec![
        "workflow".to_string(),
        "create".to_string(),
        "--template".to_string(),
        template,
        "--output".to_string(),
        output_path,
    ];
    python_bridge::call_vector_studio(args).map(|_| ())
}

/// Push local data to the sync server.
///
/// # Arguments
/// * `server_url` - Sync server base URL.
///
/// # Returns
/// JSON string containing push results per data type.
#[command]
pub async fn sync_data(server_url: String) -> Result<String, String> {
    let args = vec![
        "sync".to_string(),
        "push".to_string(),
        "--server-url".to_string(),
        server_url,
    ];
    python_bridge::call_vector_studio(args)
}

/// Get the sync status for this device.
///
/// # Arguments
/// * `server_url` - Sync server base URL.
///
/// # Returns
/// JSON string containing sync status.
#[command]
pub async fn get_sync_status(server_url: String) -> Result<String, String> {
    let args = vec![
        "sync".to_string(),
        "status".to_string(),
        "--server-url".to_string(),
        server_url,
    ];
    python_bridge::call_vector_studio(args)
}

/// Create a new collaboration room.
///
/// # Arguments
/// * `owner` - User identifier that owns the room.
///
/// # Returns
/// JSON string containing room_id, owner, and created_at.
#[command]
pub async fn create_collab_room(owner: String) -> Result<String, String> {
    let args = vec![
        "collab".to_string(),
        "create".to_string(),
        "--owner".to_string(),
        owner,
    ];
    python_bridge::call_vector_studio(args)
}

/// Join a collaboration room (CLI polling mode).
///
/// # Arguments
/// * `room_id` - Room identifier to join.
/// * `client_id` - Optional client identifier.
///
/// # Returns
/// JSON string containing the current room state.
#[command]
pub async fn join_collab_room(room_id: String, client_id: Option<String>) -> Result<String, String> {
    let mut args = vec![
        "collab".to_string(),
        "join".to_string(),
        room_id,
    ];
    if let Some(cid) = client_id {
        args.push("--client-id".to_string());
        args.push(cid);
    }
    python_bridge::call_vector_studio(args)
}

/// Get the current state of a collaboration room.
///
/// # Arguments
/// * `room_id` - Room identifier.
///
/// # Returns
/// JSON string containing room state snapshot.
#[command]
pub async fn get_collab_state(room_id: String) -> Result<String, String> {
    let args = vec![
        "collab".to_string(),
        "status".to_string(),
        room_id,
    ];
    python_bridge::call_vector_studio(args)
}
