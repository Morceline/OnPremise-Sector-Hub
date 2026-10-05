import { beforeEach, describe, expect, it } from "vitest";
import { getApiBaseUrl, setApiBaseUrl } from "../../api/client";

describe("api/client — endereço do servidor", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("usa o endereço padrão (localhost) quando nada foi configurado ainda", () => {
    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("adiciona http:// quando a pessoa digita só o IP e a porta", () => {
    const saved = setApiBaseUrl("192.168.1.10:8000");
    expect(saved).toBe("http://192.168.1.10:8000");
    expect(getApiBaseUrl()).toBe("http://192.168.1.10:8000");
  });

  it("preserva https:// quando já informado e remove barra final", () => {
    const saved = setApiBaseUrl("https://servidor.empresa.local:8000/");
    expect(saved).toBe("https://servidor.empresa.local:8000");
  });

  it("mantém o endereço salvo entre chamadas (persistência por máquina)", () => {
    setApiBaseUrl("10.0.0.5:8000");
    expect(getApiBaseUrl()).toBe("http://10.0.0.5:8000");
  });
});
