import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useItSupport } from "../../hooks/useItSupport";
import { api } from "../../api/client";

vi.mock("../../api/client", () => ({ api: { queryItSupport: vi.fn() } }));

describe("useItSupport — explique mais simples", () => {
  it("reenvia a PERGUNTA original (nunca vazia) junto com a resposta anterior", async () => {
    api.queryItSupport
      .mockResolvedValueOnce({ response: "Passo 1: reinicie o mouse." })
      .mockResolvedValueOnce({ response: "Tire o mouse e coloque de novo." });
    const { result } = renderHook(() => useItSupport());

    await act(async () => {
      await result.current.ask({ problem_description: "Meu mouse parou" });
    });
    await act(async () => {
      await result.current.simplify();
    });

    expect(api.queryItSupport).toHaveBeenLastCalledWith({
      problem_description: "Meu mouse parou",
      simplify: true,
      previous_answer: "Passo 1: reinicie o mouse.",
    });
    expect(result.current.messages.at(-1).text).toBe("Tire o mouse e coloque de novo.");
  });
});
