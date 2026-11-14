use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, WindowEvent,
};

/// Mostra e foca a janela principal (o widget).
fn mostrar_janela(app: &AppHandle) {
    if let Some(janela) = app.get_webview_window("main") {
        let _ = janela.show();
        let _ = janela.set_focus();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Ícone na bandeja do Windows: o widget continua disponível mesmo escondido.
            let abrir = MenuItem::with_id(app, "abrir", "Abrir assistente", true, None::<&str>)?;
            let encerrar = MenuItem::with_id(app, "encerrar", "Encerrar de vez", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&abrir, &encerrar])?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("Assistente de Setor")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, evento| match evento.id.as_ref() {
                    "abrir" => mostrar_janela(app),
                    "encerrar" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, evento| {
                    // Clique com o botão esquerdo no ícone: reabre o widget.
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = evento
                    {
                        mostrar_janela(tray.app_handle());
                    }
                })
                .build(app)?;
            Ok(())
        })
        .on_window_event(|janela, evento| {
            // Fechar a janela só a esconde. Para encerrar de vez, use "Encerrar de vez" na bandeja.
            if let WindowEvent::CloseRequested { api, .. } = evento {
                api.prevent_close();
                let _ = janela.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("erro ao iniciar o Assistente de Setor");
}
