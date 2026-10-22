// Impede que uma janela de console apareça atrás do widget no Windows em
// builds de release, mantendo a experiência "app leve flutuante".
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    assistente_setor_lib::run();
}
