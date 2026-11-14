import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api/client";

afterEach(() => vi.unstubAllGlobals());

describe("api/client — erro de validação do servidor", () => {
  it("vira mensagem legível, e não [object Object]", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: [{ msg: "Campo obrigatório" }] }),
      })
    );

    await expect(api.queryItSupport({ problem_description: "" })).rejects.toThrow("Campo obrigatório");
  });
});
