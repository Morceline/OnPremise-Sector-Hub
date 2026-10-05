import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useWindowChrome
 * -----------------
 * Controla o comportamento de janela pedido pelo usuário: o widget fica
 * minimizado por padrão (uma bolha pequena), pode ser expandido, arrastado
 * para qualquer canto da tela, e ao soltar o arraste "gruda" no canto mais
 * próximo — sem que isso pese no desempenho (não há loop de animação, só
 * uma transição CSS disparada uma vez no gesto de soltar).
 *
 * Detecção de ambiente: as APIs de janela do Tauri só existem quando o
 * app roda dentro do Tauri (não durante `vite dev` no navegador nem nos
 * testes com Vitest/jsdom). Por isso todo o acesso é opcional e protegido
 * — em ambiente sem Tauri, o hook vira um "no-op" gracioso.
 */

const MARGIN = 16; // distância do canto, em pixels lógicos
const EXPANDED_SIZE = { width: 360, height: 520 };
const MINIMIZED_SIZE = { width: 56, height: 56 };

function isTauriEnv() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function useWindowChrome() {
  const [isMinimized, setIsMinimized] = useState(true);
  const tauriWindowRef = useRef(null);
  const unlistenRef = useRef(null);

  useEffect(() => {
    if (!isTauriEnv()) return undefined;

    let cancelled = false;

    (async () => {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const appWindow = getCurrentWindow();
      if (cancelled) return;
      tauriWindowRef.current = appWindow;

      // Ao soltar o arraste, gruda no canto mais próximo da tela.
      const unlisten = await appWindow.onMoved(async ({ payload: position }) => {
        try {
          const monitor = await appWindow.currentMonitor();
          if (!monitor) return;

          const { width: screenW, height: screenH } = monitor.size;
          const size = isMinimized ? MINIMIZED_SIZE : EXPANDED_SIZE;

          const snapX = position.x + size.width / 2 < screenW / 2 ? MARGIN : screenW - size.width - MARGIN;
          const snapY = position.y + size.height / 2 < screenH / 2 ? MARGIN : screenH - size.height - MARGIN;

          const { LogicalPosition } = await import("@tauri-apps/api/dpi");
          await appWindow.setPosition(new LogicalPosition(snapX, snapY));
        } catch {
          // Encaixe nos cantos é um "nice-to-have" visual — uma falha aqui
          // não pode derrubar o widget nem incomodar o usuário com erro.
        }
      });

      unlistenRef.current = unlisten;
    })();

    return () => {
      cancelled = true;
      unlistenRef.current?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resizeTo = useCallback(async (size) => {
    if (!isTauriEnv() || !tauriWindowRef.current) return;
    const { LogicalSize } = await import("@tauri-apps/api/dpi");
    await tauriWindowRef.current.setSize(new LogicalSize(size.width, size.height));
  }, []);

  const minimize = useCallback(async () => {
    setIsMinimized(true);
    await resizeTo(MINIMIZED_SIZE);
  }, [resizeTo]);

  const expand = useCallback(async () => {
    setIsMinimized(false);
    await resizeTo(EXPANDED_SIZE);
  }, [resizeTo]);

  return { isMinimized, minimize, expand };
}
