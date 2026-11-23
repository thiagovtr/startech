import assert from "node:assert/strict";
import test from "node:test";
import { clienteCampanhas, ErroCampanhas, semFiltros, tamanhoPagina } from "../src/campanhas.ts";

const dados = {
  titulo: "Coleta em Lavras", hemocentro: "Hemocentro de Lavras", tipo_sanguineo: "A+",
  urgencia: "CRITICO", data_inicio: "2026-11-22", data_fim: "2026-11-30"
};
const confirmada = { ...dados, id: "campanha-1", status: "ATIVA" };
const cliente = clienteCampanhas("http://localhost:8080", async () => "token-de-teste");

test("consulta paginada envia Bearer e preserva o sinal + no filtro", async t => {
  t.mock.method(globalThis, "fetch", async (url, opcoes) => {
    assert.equal(url.origin + url.pathname, "http://localhost:8080/api/web/campanhas");
    assert.deepEqual(Object.fromEntries(new URL(url).searchParams), {
      limit: String(tamanhoPagina), offset: String(tamanhoPagina * 2), tipo_sanguineo: "A+", status: "ATIVA", vigentes: "true"
    });
    assert.equal(opcoes.headers.get("Authorization"), "Bearer token-de-teste");
    assert.equal(opcoes.headers.has("X-User-Id"), false);
    return Response.json([confirmada], { headers: { "X-Total-Count": "21" } });
  });
  assert.deepEqual(await cliente.listar({ tipo: "A+", status: "ATIVA", vigentes: true }, 2), { itens: [confirmada], total: 21 });
});

test("consulta sem filtros distingue total desconhecido de zero", async t => {
  t.mock.method(globalThis, "fetch", async url => {
    assert.deepEqual([...url.searchParams.keys()], ["limit", "offset"]);
    return Response.json([]);
  });
  assert.deepEqual(await cliente.listar(semFiltros, 0), { itens: [], total: null });
});

test("criação usa somente os campos do comando e retorna o ID da escrita", async t => {
  const requisicao = t.mock.method(globalThis, "fetch", async (url, opcoes) => {
    assert.equal(url.pathname, "/api/web/campanhas");
    assert.equal(opcoes.method, "POST");
    assert.equal(opcoes.headers.get("Content-Type"), "application/json");
    assert.equal(opcoes.headers.get("Authorization"), "Bearer token-de-teste");
    assert.deepEqual(JSON.parse(opcoes.body), dados);
    return Response.json(confirmada, { status: 201 });
  });
  assert.deepEqual(await cliente.criar(dados), confirmada);
  assert.equal(requisicao.mock.callCount(), 1);
});

test("validação do serviço preserva o motivo e o campo inválido", async t => {
  t.mock.method(globalThis, "fetch", async () => Response.json({
    title: "Dados inválidos", detail: "Confira o período.", invalidParams: [{ name: "data_fim", reason: "Anterior ao início" }]
  }, { status: 400, headers: { "Content-Type": "application/problem+json" } }));
  await assert.rejects(cliente.criar(dados), /Confira o período.*data_fim: Anterior ao início/);
});

for (const status of [401, 403, 502, 503, 504]) {
  test("HTTP " + status + " mantém o detalhe do serviço e não repete o comando", async t => {
    const requisicao = t.mock.method(globalThis, "fetch", async () => Response.json({ detail: "Detalhe de origem" }, {
      status, headers: { "Content-Type": "application/problem+json" }
    }));
    await assert.rejects(cliente.criar(dados), e => e instanceof ErroCampanhas && e.status === status && e.message.includes("Detalhe de origem"));
    assert.equal(requisicao.mock.callCount(), 1);
  });
}

test("uma sessão sem token impede a chamada ao Gateway", async t => {
  const requisicao = t.mock.method(globalThis, "fetch");
  const expirado = clienteCampanhas("http://localhost:8080", async () => { throw new Error("Sessão expirada"); });
  await assert.rejects(expirado.criar(dados), /Sessão expirada/);
  assert.equal(requisicao.mock.callCount(), 0);
});

test("falha de rede durante o POST não gera nova tentativa", async t => {
  const requisicao = t.mock.method(globalThis, "fetch", async () => { throw new TypeError("Failed to fetch"); });
  await assert.rejects(cliente.criar(dados), e => e instanceof ErroCampanhas && e.status === 0);
  assert.equal(requisicao.mock.callCount(), 1);
});
