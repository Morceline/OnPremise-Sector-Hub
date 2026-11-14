import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useWindowChrome } from "../../hooks/useWindowChrome";

// No jsdom não existe a janela nativa do Tauri: é o mesmo cenário de abrir o
// app no navegador (npm run dev).
describe("useWindowChrome fora do Tauri", () => {
  it("começa minimizado e alterna minimizar/expandir sem quebrar", async () => {
    const { result } = renderHook(() => useWindowChrome());
    expect(result.current.isMinimized).toBe(true);

    await act(async () => {
      await result.current.expand();
    });
    expect(result.current.isMinimized).toBe(false);

    await act(async () => {
      await result.current.minimize();
    });
    expect(result.current.isMinimized).toBe(true);
  });

  it("hideToTray() devolve false fora do Tauri, sem fingir que escondeu", async () => {
    const { result } = renderHook(() => useWindowChrome());

    let hidden;
    await act(async () => {
      hidden = await result.current.hideToTray();
    });

    expect(hidden).toBe(false);
  });
});
