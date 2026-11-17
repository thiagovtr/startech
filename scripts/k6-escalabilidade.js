import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Métricas customizadas por subsistema distribuído
const latenciaLeituraCQRS = new Trend('latencia_leitura_cqrs', true);
const latenciaEscritaOutbox = new Trend('latencia_escrita_outbox', true);
const latenciaBordaBFF = new Trend('latencia_borda_bff', true);
const campanhasCriadasOutbox = new Counter('campanhas_criadas_outbox');
const taxaSucessoGlobal = new Rate('taxa_sucesso_global');

const HEMOCENTROS_BASE = __ENV.HEMOCENTROS_BASE || 'http://172.29.0.2:30080';
const GATEWAY_BASE = __ENV.GATEWAY_BASE || 'http://172.29.0.2:30088';

export const options = {
  scenarios: {
    // 1. Estresse de Leitura CQRS (MongoDB Read View) para acionar o HPA (CPU > 70% de 200m = 140m)
    cqrs_leitura_estresse: {
      executor: 'ramping-vus',
      exec: 'cenarioLeituraCQRS',
      startVUs: 5,
      stages: [
        { duration: '15s', target: 30 },  // Aquecimento e subida inicial de carga
        { duration: '30s', target: 75 },  // Carga alta (>140m CPU): dispara HPA (1 -> 2 -> 3 réplicas)
        { duration: '35s', target: 95 },  // Pico sustentado distribuído entre as 3 réplicas
        { duration: '10s', target: 20 },  // Redução gradual (cooldown)
        { duration: '5s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
    // 2. Escrita Concorrente CQRS + Transactional Outbox (PostgreSQL -> SKIP LOCKED -> RabbitMQ -> MongoDB)
    cqrs_escrita_outbox: {
      executor: 'constant-arrival-rate',
      exec: 'cenarioEscritaOutbox',
      rate: 4,
      timeUnit: '1s',
      duration: '85s',
      preAllocatedVUs: 8,
      maxVUs: 20,
      startTime: '5s',
    },
    // 3. Fluxo de Borda Distribuído (API Gateway + JWT RS256 + BFF Mobile & BFF Web)
    borda_gateway_bff: {
      executor: 'constant-arrival-rate',
      exec: 'cenarioBordaBFF',
      rate: 12,
      timeUnit: '1s',
      duration: '85s',
      preAllocatedVUs: 10,
      maxVUs: 25,
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
  for (let i = 0; i < 12; i++) {
    const tipo = tipos[i % tipos.length];
    http.post(
      `${HEMOCENTROS_BASE}/api/v1/campanhas`,
      JSON.stringify({
        titulo: `Alerta Estoque ${tipo} #${i + 1}`,
        hemocentro: 'Hemocentro Regional de Lavras',
        tipo_sanguineo: tipo,
        urgencia: i % 2 === 0 ? 'CRITICO' : 'ALTO',
        data_inicio: '2026-11-10',
        data_fim: '2026-12-20',
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
  // Rotaciona a conexão TCP a cada 25 iterações para o kube-proxy distribuir carga às novas réplicas sem exaurir portas efêmeras
  const headers = __ITER % 25 === 0 ? { Connection: 'close' } : {};
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
    titulo: `Campanha K6 Outbox VU${__VU}-${__ITER}`,
    hemocentro: 'Hemocentro Regional de Lavras',
    tipo_sanguineo: 'O-',
    urgencia: 'CRITICO',
    data_inicio: '2026-11-15',
    data_fim: '2026-12-30',
  });

  const res = http.post(`${HEMOCENTROS_BASE}/api/v1/campanhas`, payload, {
    headers: { 'Content-Type': 'application/json' },
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
