package br.ufla.startech.agendamentos.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.repository.AgendamentoRepository;
import br.ufla.startech.agendamentos.repository.SlotRepository;

/** Passos 1 e 4 da SAGA, compensação do passo 1 e grade de horários, contra um PostgreSQL real. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("demo")
@Testcontainers(disabledWithoutDocker = true)
class ReservaControllerTests {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configureDataSource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private SlotRepository slots;

    @Autowired
    private AgendamentoRepository agendamentos;

    @Test
    void reservaCriaAgendamentoProvisorioEOcupaVaga() throws Exception {
        Slot slot = slot(2);
        String ag = id("ag");

        reservar(slot.getId(), ag, id("doador"), "saga-1-step1")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.agendamentoId").value(ag))
                .andExpect(jsonPath("$.slotId").value(slot.getId()))
                .andExpect(jsonPath("$.dataHoraInicio").value(slot.getDataHoraInicio().toString()))
                .andExpect(jsonPath("$.dataHoraFim").exists())
                .andExpect(jsonPath("$.status").value("CRIADO_PROVISORIO"));

        assertThat(vagas(slot)).isEqualTo(1);
    }

    @Test
    void repetirAReservaNaoOcupaOutraVaga() throws Exception {
        Slot slot = slot(2);
        String ag = id("ag");
        String doador = id("doador");

        reservar(slot.getId(), ag, doador, "saga-1-step1").andExpect(status().isCreated());
        reservar(slot.getId(), ag, doador, "saga-1-step1")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("CRIADO_PROVISORIO"));

        assertThat(vagas(slot)).isEqualTo(1);
    }

    @Test
    void slotEsgotadoResponde409() throws Exception {
        Slot slot = slot(0);
        reservar(slot.getId(), id("ag"), id("doador"), "k")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:slot-esgotado"));
    }

    @Test
    void slotInexistenteResponde404() throws Exception {
        reservar("slot-nao-existe", id("ag"), id("doador"), "k")
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("urn:startech:error:slot-nao-encontrado"));
    }

    @Test
    void doadorComAgendamentoAtivoResponde409Rn09() throws Exception {
        String doador = id("doador");
        reservar(slot(2).getId(), id("ag"), doador, "k1").andExpect(status().isCreated());

        reservar(slot(2).getId(), id("ag"), doador, "k2")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-ativo"));
    }

    @Test
    void corpoInvalidoResponde400() throws Exception {
        mockMvc.perform(post("/api/v1/slots/{id}/reservas", slot(1).getId())
                        .contentType(MediaType.APPLICATION_JSON).content("{\"agendamentoId\": \"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.type").value("urn:startech:error:requisicao-invalida"));
    }

    @Test
    void compensacaoDevolveAVagaEEIdempotente() throws Exception {
        Slot slot = slot(2);
        String ag = id("ag");
        reservar(slot.getId(), ag, id("doador"), "k").andExpect(status().isCreated());

        mockMvc.perform(delete("/api/v1/slots/{s}/reservas/{a}", slot.getId(), ag)).andExpect(status().isNoContent());
        mockMvc.perform(delete("/api/v1/slots/{s}/reservas/{a}", slot.getId(), ag)).andExpect(status().isNoContent());

        assertThat(vagas(slot)).isZero();
        assertThat(agendamentos.findById(ag).orElseThrow().getStatus())
                .isEqualTo(StatusAgendamento.CANCELADO_COMPENSACAO_SAGA);
    }

    @Test
    void compensarReservaInexistenteResponde204() throws Exception {
        mockMvc.perform(delete("/api/v1/slots/{s}/reservas/{a}", "slot-x", "ag-x")).andExpect(status().isNoContent());
    }

    @Test
    void confirmacaoMudaParaConfirmadoEEIdempotente() throws Exception {
        String ag = id("ag");
        reservar(slot(2).getId(), ag, id("doador"), "k").andExpect(status().isCreated());

        mockMvc.perform(post("/api/v1/agendamentos/{id}/confirmacao", ag))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CONFIRMADO"))
                .andExpect(jsonPath("$._links.cancelar").exists());
        mockMvc.perform(post("/api/v1/agendamentos/{id}/confirmacao", ag))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CONFIRMADO"));
    }

    @Test
    void confirmarCompensadoResponde409() throws Exception {
        Slot slot = slot(2);
        String ag = id("ag");
        reservar(slot.getId(), ag, id("doador"), "k").andExpect(status().isCreated());
        mockMvc.perform(delete("/api/v1/slots/{s}/reservas/{a}", slot.getId(), ag));

        mockMvc.perform(post("/api/v1/agendamentos/{id}/confirmacao", ag))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-ja-cancelado"));
        mockMvc.perform(post("/api/v1/agendamentos/{id}/confirmacao", "nao-existe"))
                .andExpect(status().isNotFound());
    }

    @Test
    void duasReservasNaUltimaVagaSoUmaPassa() throws Exception {
        Slot slot = slot(1);
        int tentativas = 6;
        CountDownLatch largada = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(tentativas);
        List<Future<Integer>> resultados = new ArrayList<>();
        for (int i = 0; i < tentativas; i++) {
            Callable<Integer> tarefa = () -> {
                largada.await();
                return reservar(slot.getId(), id("ag"), id("doador"), "k").andReturn().getResponse().getStatus();
            };
            resultados.add(pool.submit(tarefa));
        }
        largada.countDown();
        List<Integer> status = new ArrayList<>();
        for (Future<Integer> f : resultados) {
            status.add(f.get());
        }
        pool.shutdown();

        assertThat(status).containsOnly(201, 409);
        assertThat(status.stream().filter(s -> s == 201)).hasSize(1);
        assertThat(vagas(slot)).isEqualTo(1);
    }

    @Test
    void listagemTrazSoSlotsFuturosComVagaELinkAgendar() throws Exception {
        Slot comVaga = slot(2);
        Slot esgotado = slot(0);
        Instant passado = Instant.now().minus(Duration.ofDays(1));
        Slot antigo = slots.save(new Slot(id("slot"), "posto-1", passado, passado.plusSeconds(1200), 2, 0));

        mockMvc.perform(get("/api/v1/slots"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.itens[*].slotId", hasItem(comVaga.getId())))
                .andExpect(jsonPath("$.itens[*].slotId", not(hasItem(esgotado.getId()))))
                .andExpect(jsonPath("$.itens[*].slotId", not(hasItem(antigo.getId()))))
                .andExpect(jsonPath("$.itens[0]._links.agendar.href").value("/api/v1/sagas/agendamento"))
                .andExpect(jsonPath("$.itens[0]._links.agendar.method").value("POST"));
        mockMvc.perform(get("/api/v1/slots").param("postoId", "posto-que-nao-existe"))
                .andExpect(jsonPath("$.itens").isEmpty());
    }

    @Test
    void gradeDeDemonstracaoECriadaNaSubida() throws Exception {
        mockMvc.perform(get("/api/v1/slots"))
                .andExpect(jsonPath("$.itens[*].slotId", hasItem("slot-futuro")))
                .andExpect(jsonPath("$.itens[*].slotId", hasItem("slot-proximo")))
                .andExpect(jsonPath("$.itens[*].slotId", not(hasItem("slot-lotado"))));
        assertThat(slots.existsById("slot-lotado")).isTrue();
    }

    private ResultActions reservar(String slotId, String agendamentoId, String doadorId, String chave)
            throws Exception {
        return mockMvc.perform(post("/api/v1/slots/{id}/reservas", slotId)
                .header("Idempotency-Key", chave)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"agendamentoId\": \"" + agendamentoId + "\", \"doadorId\": \"" + doadorId + "\"}"));
    }

    private Slot slot(int capacidade) {
        Instant inicio = Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS).plus(Duration.ofDays(10));
        return slots.save(new Slot(id("slot"), "posto-1", inicio, inicio.plus(Duration.ofMinutes(20)), capacidade, 0));
    }

    private int vagas(Slot slot) {
        return slots.findById(slot.getId()).orElseThrow().getVagasOcupadas();
    }

    private static String id(String prefixo) {
        return prefixo + "-" + UUID.randomUUID().toString().substring(0, 18);
    }
}
