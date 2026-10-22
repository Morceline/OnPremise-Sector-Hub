import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListEditor } from "../../components/admin/ListEditor";

describe("ListEditor", () => {
  it("adiciona um item novo e limpa o campo de digitação", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ListEditor items={[]} onChange={onChange} placeholder="Digite..." />);
    await user.type(screen.getByPlaceholderText("Digite..."), "C:\\Manuais");
    await user.click(screen.getByText("Adicionar"));

    expect(onChange).toHaveBeenCalledWith(["C:\\Manuais"]);
  });

  it("não adiciona item duplicado", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ListEditor items={["C:\\Manuais"]} onChange={onChange} placeholder="Digite..." />);
    await user.type(screen.getByPlaceholderText("Digite..."), "C:\\Manuais");
    await user.click(screen.getByText("Adicionar"));

    expect(onChange).not.toHaveBeenCalled();
  });

  it("remove um item existente", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(<ListEditor items={["C:\\Manuais", "C:\\RH"]} onChange={onChange} placeholder="Digite..." />);
    await user.click(screen.getByLabelText("Remover C:\\Manuais"));

    expect(onChange).toHaveBeenCalledWith(["C:\\RH"]);
  });
});
