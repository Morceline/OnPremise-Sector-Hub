# Ícones do aplicativo

Os arquivos desta pasta são um **placeholder gerado automaticamente**
(um círculo na cor "ardósia" do tema com a letra "A"), só para o
`npm run tauri build` não falhar por falta de ícone. Troque pelo logo real
da empresa antes de distribuir o instalador de verdade.

## Como trocar pelo logo real

1. Tenha um logo quadrado, de preferência 1024×1024px, em PNG com fundo
   transparente.
2. Na pasta `frontend/`, rode:
```bash
   npx tauri icon caminho/para/seu-logo.png
```
3. O comando sobrescreve automaticamente todos os arquivos desta pasta nos
   formatos que `tauri.conf.json` espera (`32x32.png`, `128x128.png`,
   `128x128@2x.png`, `icon.icns`, `icon.ico`), além dos ícones extras do
   pacote Windows Store (`Square*.png`, `StoreLogo.png` — só usados se você
   gerar um pacote `.msix`).

Este comando roda em qualquer máquina com Node (não precisa de Rust/Cargo
instalado) — foi assim que os placeholders desta pasta foram gerados.