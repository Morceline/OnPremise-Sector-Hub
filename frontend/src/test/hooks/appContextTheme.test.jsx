import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppProvider } from "../../state/AppContext";
import { PreferencesPanel } from "../../components/PreferencesPanel";

vi.mock("../../api/client", () => ({
  api: {
    health: vi.fn().mockResolvedValue({ status: "online" }),
    getActiveConfig: vi.fn().mockResolvedValue({ configured: false }),
  },
}));

describe("AppContext — persistência do tema", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("inicia com o tema salvo anteriormente, não sempre 'system'", async () => {
    localStorage.setItem("assistente-setor:theme", "dark");

    render(
      <AppProvider>
        <PreferencesPanel onBack={() => {}} />
      </AppProvider>
    );

    await screen.findByText("Voltar");
    expect(screen.getByLabelText("Escuro")).toBeChecked();
  });
});