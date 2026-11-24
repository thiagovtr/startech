import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Métricas customizadas por subsistema distribuído
const latenciaLeituraCQRS = new Trend('latencia_leitura_cqrs', true);
const latenciaEscritaOutbox = new Trend('latencia_escrita_outbox', true);
const latenciaBordaBFF = new Trend('latencia_borda_bff', true);
const campanhasCriadasOutbox = new Counter('campanhas_criadas_outbox');
const taxaSucessoGlobal = new Rate('taxa_sucesso_global');

const HEMOCENTROS_BASE = __ENV.HEMOCENTROS_BASE || 'http://ms-hemocentros:8000';
const GATEWAY_BASE = __ENV.GATEWAY_BASE || 'http://gateway:8080';
const RODADA = __ENV.RODADA || '1-replica';

export const options = {
  scenarios: {
    // 1. Estresse de Leitura CQRS (MongoDB Read View) distribuído entre réplicas do ms-hemocentros
    cqrs_leitura_estresse: {
      executor: 'ramping-vus',
      exec: 'cenarioLeituraCQRS',
      startVUs: 5,
      stages: [
        { duration: '10s', target: 30 },
        { duration: '25s', target: 60 },
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
    // 2. Escrita Concorrente CQRS + Transactional Outbox (PostgreSQL -> SKIP LOCKED -> RabbitMQ -> MongoDB)
    cqrs_escrita_outbox: {
      executor: 'constant-arrival-rate',
      exec: 'cenarioEscritaOutbox',
      rate: 4,
      timeUnit: '1s',
      duration: '35s',
      preAllocatedVUs: 6,
      maxVUs: 15,
      startTime: '5s',
    },
    // 3. Fluxo de Borda Distribuído (API Gateway + JWT RS256 + BFF Mobile & BFF Web)
    borda_gateway_bff: {
      executor: 'constant-arrival-rate',
      exec: 'cenarioBordaBFF',
      rate: 10,
      timeUnit: '1s',
      duration: '35s',
      preAllocatedVUs: 8,
      maxVUs: 20,
      startTime: '5s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    latencia_leitura_cqrs: ['p(95)<400'],
    latencia_escrita_outbox: ['p(95)<500'],
    latencia_borda_bff: ['p(95)<600'],
    taxa_sucesso_global: ['rate>0.99'],
    checks: ['rate>0.99'],
  },
};

export function setup() {
  const tokenUrl = `${GATEWAY_BASE}/realms/startech/protocol/openid-connect/token`;

  const respDoador = http.post(tokenUrl, {
    client_id: 'mobile',
    grant_type: 'password',
    username: 'doador1',
    password: 'doador123',
  });

  const respOperador = http.post(tokenUrl, {
    client_id: 'web',
    grant_type: 'password',
    username: 'operador1',
    password: 'operador123',
  });

  const tokenDoador = respDoador.json('access_token');
  const tokenOperador = respOperador.json('access_token');

  // Semeia campanhas iniciais para popular a view de leitura do MongoDB
  const tipos = ['O-', 'O+', 'A-', 'A+', 'B-', 'AB-'];
  for (let i = 0; i < 6; i++) {
    const tipo = tipos[i % tipos.length];
    http.post(
      `${HEMOCENTROS_BASE}/api/v1/campanhas`,
      JSON.stringify({
        titulo: `Campanha Base ${tipo} #${i + 1}`,
        hemocentro: 'Hemocentro Regional de Lavras',
        tipo_sanguineo: tipo,
        urgencia: i % 2 === 0 ? 'CRITICO' : 'NORMAL',
        data_inicio: '2026-11-20',
        data_fim: '2026-12-31',
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
  }

  sleep(2);
  return { tokenDoador, tokenOperador };
}

export function cenarioLeituraCQRS() {
  const filtros = [
    'tipo_sanguineo=O-&vigentes=true&limit=50',
    'tipo_sanguineo=O-&status=ATIVA&limit=50',
    'vigentes=true&limit=100',
  ];
  const qs = filtros[__ITER % filtros.length];
  // Rotaciona a conexão TCP a cada 10 iterações para o DNS round-robin do Docker distribuir carga entre as réplicas
  const headers = __ITER % 10 === 0 ? { Connection: 'close' } : {};
  const res = http.get(`${HEMOCENTROS_BASE}/api/v1/campanhas?${qs}`, {
    headers,
    tags: { cenario: 'cqrs_leitura' },
  });

  latenciaLeituraCQRS.add(res.timings.duration);
  const ok = check(res, {
    'CQRS GET /api/v1/campanhas status 200': (r) => r.status === 200,
    'CQRS GET possui X-Total-Count': (r) => r.headers['X-Total-Count'] !== undefined,
  });
  taxaSucessoGlobal.add(ok);
  sleep(0.04);
}

export function cenarioEscritaOutbox() {
  const payload = JSON.stringify({
    titulo: `Campanha K6 Outbox ${RODADA} VU${__VU}-${__ITER}`,
    hemocentro: 'Hemocentro Regional de Lavras',
    tipo_sanguineo: 'O-',
    urgencia: 'CRITICO',
    data_inicio: '2026-11-20',
    data_fim: '2026-12-31',
  });

  const res = http.post(`${HEMOCENTROS_BASE}/api/v1/campanhas`, payload, {
    headers: { 'Content-Type': 'application/json', Connection: 'close' },
    tags: { cenario: 'cqrs_escrita_outbox' },
  });

  latenciaEscritaOutbox.add(res.timings.duration);
  const ok = check(res, {
    'Outbox POST /api/v1/campanhas status 201': (r) => r.status === 201,
  });
  if (ok) {
    campanhasCriadasOutbox.add(1);
  }
  taxaSucessoGlobal.add(ok);
}

export function cenarioBordaBFF(data) {
  if (__ITER % 2 === 0) {
    const res = http.get(`${GATEWAY_BASE}/api/mobile/home`, {
      headers: { Authorization: `Bearer ${data.tokenDoador}` },
      tags: { cenario: 'borda_bff_mobile' },
    });
    latenciaBordaBFF.add(res.timings.duration);
    const ok = check(res, {
      'Gateway -> BFF Mobile /api/mobile/home 200': (r) => r.status === 200,
    });
    taxaSucessoGlobal.add(ok);
  } else {
    const res = http.get(`${GATEWAY_BASE}/api/web/campanhas?tipo_sanguineo=O-&limit=20`, {
      headers: { Authorization: `Bearer ${data.tokenOperador}` },
      tags: { cenario: 'borda_bff_web' },
    });
    latenciaBordaBFF.add(res.timings.duration);
    const ok = check(res, {
      'Gateway -> BFF Web /api/web/campanhas 200': (r) => r.status === 200,
    });
    taxaSucessoGlobal.add(ok);
  }
}

export function handleSummary(data) {
  const m = data.metrics;
  const resumo = {
    rodada: RODADA,
    reqs_total: m.http_reqs?.values?.count ?? 0,
    reqs_por_seg: Number((m.http_reqs?.values?.rate ?? 0).toFixed(2)),
    sucesso_pct: Number(((1 - (m.http_req_failed?.values?.rate ?? 0)) * 100).toFixed(2)),
    checks_pct: Number(((m.checks?.values?.rate ?? 0) * 100).toFixed(2)),
    http_med_ms: Number((m.http_req_duration?.values?.med ?? 0).toFixed(2)),
    http_p90_ms: Number((m.http_req_duration?.values?.['p(90)'] ?? 0).toFixed(2)),
    http_p95_ms: Number((m.http_req_duration?.values?.['p(95)'] ?? 0).toFixed(2)),
    cqrs_leitura_med_ms: Number((m.latencia_leitura_cqrs?.values?.med ?? 0).toFixed(2)),
    cqrs_leitura_p95_ms: Number((m.latencia_leitura_cqrs?.values?.['p(95)'] ?? 0).toFixed(2)),
    outbox_escrita_med_ms: Number((m.latencia_escrita_outbox?.values?.med ?? 0).toFixed(2)),
    outbox_escrita_p95_ms: Number((m.latencia_escrita_outbox?.values?.['p(95)'] ?? 0).toFixed(2)),
    borda_bff_med_ms: Number((m.latencia_borda_bff?.values?.med ?? 0).toFixed(2)),
    borda_bff_p95_ms: Number((m.latencia_borda_bff?.values?.['p(95)'] ?? 0).toFixed(2)),
    campanhas_criadas: m.campanhas_criadas_outbox?.values?.count ?? 0,
    vus_max: m.vus_max?.values?.max ?? 0,
  };
  return {
    stdout: `\n=== RESUMO_K6_JSON (${RODADA}) ===\n${JSON.stringify(resumo)}\n`,
  };
}
