/**
 * api/client.js
 * ---------------
 * Cliente único para todas as chamadas ao backend.
 *
 * IMPORTANTE — por que o endereço do backend não é fixo:
 * Só a máquina do SERVIDOR roda o backend localmente (localhost:8000).
 * Nas máquinas dos colaboradores, o widget precisa falar com o backend
 * pela rede (ex: "http://192.168.1.10:8000"). Por isso o endereço fica
 * salvo em localStorage (por máquina, nunca sincronizado) em vez de
 * hardcoded — sem isso, seria preciso gerar um instalador diferente para
 * cada máquina, o que não escala. Ver components/ServerSetup.jsx, a tela
 * que pede esse endereço na primeira vez que o backend não responde no
 * endereço padrão.
 */

const STORAGE_KEY = "assistente-setor:api-base-url";
const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function normalizeBaseUrl(value) {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (!trimmed) return trimmed;
  return /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
}

export function getApiBaseUrl() {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE_URL;
  } catch {
    // localStorage pode falhar em contextos restritos — cai para o padrão.
    return DEFAULT_BASE_URL;
  }
}

export function setApiBaseUrl(value) {
  const normalized = normalizeBaseUrl(value);
  try {
    localStorage.setItem(STORAGE_KEY, normalized);
  } catch {
    // Falha ao persistir não deve quebrar a sessão atual.
  }
  return normalized;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, managerKey } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (managerKey) headers["X-Manager-Key"] = managerKey;

  let response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    // Falha de rede real (backend fora do ar ou endereço errado) —
    // mensagem em linguagem simples, já que quem vai ler isso é um
    // colaborador.
    throw new ApiError("Não foi possível falar com o assistente. Confira se o servidor está ligado.", 0);
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // resposta sem corpo JSON (ex: 204) — segue sem payload
  }

  if (!response.ok) {
    const detail = payload?.detail || "Ocorreu um erro inesperado.";
    throw new ApiError(detail, response.status);
  }

  return payload;
}

export const api = {
  health: () => request("/health"),

  sendChatMessage: (message, sessionId) =>
    request("/api/v1/chat/query", { method: "POST", body: { message, session_id: sessionId } }),

  queryItSupport: (payload) => request("/api/v1/it-support/query", { method: "POST", body: payload }),

  submitFeedback: (payload) => request("/api/v1/feedback/submit", { method: "POST", body: payload }),

  getActiveConfig: () => request("/api/v1/config/active"),

  saveConfig: (config, managerKey) =>
    request("/api/v1/config/save", { method: "POST", body: config, managerKey }),
};

export { ApiError };
