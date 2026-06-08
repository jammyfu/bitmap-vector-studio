//! Main entry point for the Bitmap Vector Studio Tauri desktop application.
//!
//! Initializes the Tauri runtime, registers all IPC commands, and sets up
//! the native application menu.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod python_bridge;
mod updater;

use tauri::{CustomMenuItem, Menu, MenuItem, Submenu};

/// Build the native application menu (File, Edit, View, Help).
fn build_menu() -> Menu {
    // File menu
    let open = CustomMenuItem::new("open", "Open...").accelerator("cmdOrControl+O");
    let quit = CustomMenuItem::new("quit", "Quit").accelerator("cmdOrControl+Q");
    let file_menu = Submenu::new(
        "File",
        Menu::new()
            .add_item(open)
            .add_native_item(MenuItem::Separator)
            .add_item(quit),
    );

    // Edit menu
    let edit_menu = Submenu::new(
        "Edit",
        Menu::new()
            .add_native_item(MenuItem::Undo)
            .add_native_item(MenuItem::Redo)
            .add_native_item(MenuItem::Separator)
            .add_native_item(MenuItem::Cut)
            .add_native_item(MenuItem::Copy)
            .add_native_item(MenuItem::Paste)
            .add_native_item(MenuItem::SelectAll),
    );

    // View menu
    let reload = CustomMenuItem::new("reload", "Reload").accelerator("cmdOrControl+R");
    let view_menu = Submenu::new(
        "View",
        Menu::new()
            .add_item(reload)
            .add_native_item(MenuItem::Separator)
            .add_native_item(MenuItem::EnterFullScreen)
            .add_native_item(MenuItem::Separator)
            .add_native_item(MenuItem::Minimize)
            .add_native_item(MenuItem::CloseWindow),
    );

    // Help menu
    let about = CustomMenuItem::new("about", "About Bitmap Vector Studio");
    let help_menu = Submenu::new("Help", Menu::new().add_item(about));

    Menu::new()
        .add_submenu(file_menu)
        .add_submenu(edit_menu)
        .add_submenu(view_menu)
        .add_submenu(help_menu)
}

fn main() {
    let menu = build_menu();

    tauri::Builder::default()
        .menu(menu)
        .on_menu_event(|event| {
            match event.menu_item_id() {
                "open" => {
                    let window = event.window();
                    let _ = window.emit("menu-open", ());
                }
                "quit" => {
                    std::process::exit(0);
                }
                "reload" => {
                    let window = event.window();
                    let _ = window.eval("window.location.reload()");
                }
                "about" => {
                    let window = event.window();
                    let _ = window.emit("menu-about", ());
                }
                _ => {}
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::convert_image,
            commands::batch_convert,
            commands::get_presets,
            commands::save_preset,
            commands::delete_preset,
            commands::get_history,
            commands::recommend_preset,
            commands::open_with_editor,
            commands::get_plugins,
            commands::enable_plugin,
            commands::disable_plugin,
            commands::get_config,
            commands::set_config,
            commands::market_list,
            commands::market_install,
            commands::start_queue,
            commands::pause_queue,
            commands::cancel_queue,
            commands::get_queue_status,
            commands::open_file_dialog,
            commands::open_output_folder,
            commands::start_api,
            commands::stop_api,
            commands::check_env,
            commands::get_ocr_languages,
            commands::detect_text_regions_multilang,
            commands::recognize_text_multilang,
            commands::prewarm_env,
            commands::get_performance_stats,
            updater::check_update,
            updater::download_update,
            updater::install_update,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
