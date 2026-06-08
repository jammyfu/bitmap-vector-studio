//! Tauri auto-updater integration for Bitmap Vector Studio.
//!
//! Provides IPC commands for checking, downloading, and installing updates
//! from GitHub Releases.

use tauri::{AppHandle, Runtime};

/// Check if a newer version is available.
///
/// Returns `Some(version_string)` when an update exists, or `None` if the
/// app is already on the latest release.
#[tauri::command]
pub async fn check_update<R: Runtime>(app: AppHandle<R>) -> Result<Option<String>, String> {
    let updater = app.updater();
    match updater.check().await {
        Ok(update) => Ok(Some(update.latest_version().to_string())),
        Err(e) => {
            // Tauri returns an error when no update is available.
            // Treat "up to date" as None rather than a failure.
            let msg = e.to_string().to_lowercase();
            if msg.contains("up to date")
                || msg.contains("no update")
                || msg.contains("404")
                || msg.contains("not found")
            {
                Ok(None)
            } else {
                Err(format!("Update check failed: {}", e))
            }
        }
    }
}

/// Download the update package.
///
/// **Note**: Tauri v1.8 combines download and install into a single
/// `download_and_install()` operation. This command performs both steps
/// and returns empty bytes. In practice, call `install_update` directly
/// for a cleaner API.
#[tauri::command]
pub async fn download_update<R: Runtime>(app: AppHandle<R>) -> Result<Vec<u8>, String> {
    let updater = app.updater();
    let update = updater
        .check()
        .await
        .map_err(|e| e.to_string())?;

    // Tauri v1.8 does not expose a separate download() method.
    // We perform the combined download+install and return empty bytes.
    update
        .download_and_install()
        .await
        .map_err(|e| format!("Download failed: {}", e))?;
    Ok(vec![])
}

/// Download and install the update, then request a relaunch.
#[tauri::command]
pub async fn install_update<R: Runtime>(app: AppHandle<R>) -> Result<(), String> {
    let updater = app.updater();
    let update = updater
        .check()
        .await
        .map_err(|e| e.to_string())?;

    update
        .download_and_install()
        .await
        .map_err(|e| format!("Install failed: {}", e))?;

    // Ask the application to restart so the new version takes effect.
    app.restart();
    Ok(())
}
