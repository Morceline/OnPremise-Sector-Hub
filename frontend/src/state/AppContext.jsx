import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AppContext = createContext(null);

// Mapeia o setor cadastrado pelo gestor para uma das 3 paletas visuais
// prontas (ver theme.css). Evita expor um seletor de cor livre ao gestor —
// decisão de UX da etapa 4: cor livre gera inconsistência visual entre
// instalações sem trazer benefício real para quem usa o chat.
const SECTOR_TO_PALETTE = {
  juridico: "marinho",
  militar: "marinho",
  recursos_humanos: "marinho",
  saude: "oliva",
  alimenticio: "oliva",
  financeiro: "ardosia",
  operacional: "ardosia",
  outro: "ardosia",
};

export function AppProvider({ children }) {
  const [view, setView] = useState("chat"); // chat | it-support | admin-gate | admin-form | feedback
  const [sectorConfig, setSectorConfig] = useState(null);
  const [health, setHealth] = useState({ status: "unknown" });
  const [theme, setTheme] = useState("system"); // system | light | dark

  const refreshConfig = useCallback(async () => {
    try {
      const config = await api.getActiveConfig();
      setSectorConfig(config);
    } catch {
      setSectorConfig({ configured: false });
    }
  }, []);

  const refreshHealth = useCallback(async () => {
    try {
      const result = await api.health();
      setHealth(result);
    } catch {
      setHealth({ status: "offline", dependencies: { qdrant: false, ollama: false } });
    }
  }, []);

  useEffect(() => {
    refreshConfig();
    refreshHealth();
    // Verifica saúde do backend periodicamente, mas com intervalo generoso
    // (60s) para não gerar tráfego/CPU desnecessário em background.
    const interval = setInterval(refreshHealth, 60_000);
    return () => clearInterval(interval);
  }, [refreshConfig, refreshHealth]);

  const palette = useMemo(() => {
    const sectorType = sectorConfig?.sector_type;
    return SECTOR_TO_PALETTE[sectorType] || "ardosia";
  }, [sectorConfig]);

  const value = useMemo(
    () => ({
      view,
      setView,
      sectorConfig,
      refreshConfig,
      health,
      refreshHealthNow: refreshHealth,
      theme,
      setTheme,
      palette,
    }),
    [view, sectorConfig, refreshConfig, health, refreshHealth, theme, palette]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppState precisa estar dentro de um <AppProvider>");
  return ctx;
}
