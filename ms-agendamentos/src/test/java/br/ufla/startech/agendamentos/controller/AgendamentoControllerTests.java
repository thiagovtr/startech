package br.ufla.startech.agendamentos.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.repository.AgendamentoRepository;
import br.ufla.startech.agendamentos.repository.SlotRepository;

/** Consulta, listagem e cancelamento com HATEOAS (contratos §3) contra um PostgreSQL real. */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class AgendamentoControllerTests {

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
    void confirmadoNoPrazoTemSelfECancelar() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(3), "doador-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos/{id}", ag.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CONFIRMADO"))
                .andExpect(jsonPath("$.concluido").value(false))
                .andExpect(jsonPath("$.slot.slotId").value(ag.getSlot().getId()))
                .andExpect(jsonPath("$.disclaimerLegal").exists())
                .andExpect(jsonPath("$._links.self.href").value("/api/v1/agendamentos/" + ag.getId()))
                .andExpect(jsonPath("$._links.cancelar.href")
                        .value("/api/v1/agendamentos/" + ag.getId() + "/cancelamento"))
                .andExpect(jsonPath("$._links.cancelar.method").value("POST"))
                .andExpect(jsonPath("$._links.novo-agendamento").doesNotExist());
    }

    @Test
    void cancelarLiberaVagaETrocaOsLinks() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(3), "doador-" + UUID.randomUUID());

        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId())
                        .contentType(MediaType.APPLICATION_JSON).content("{\"motivo\": \"Imprevisto pessoal\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELADO_DOADOR"))
                .andExpect(jsonPath("$.motivo").value("Imprevisto pessoal"))
                .andExpect(jsonPath("$.dataCancelamento").exists())
                .andExpect(jsonPath("$.slotLiberado").value(ag.getSlot().getId()))
                .andExpect(jsonPath("$._links.self").exists())
                .andExpect(jsonPath("$._links.cancelar").doesNotExist())
                .andExpect(jsonPath("$._links.novo-agendamento.href").value("/api/v1/sagas/agendamento"));

        assertThat(slots.findById(ag.getSlot().getId()).orElseThrow().getVagasOcupadas()).isZero();
    }

    @Test
    void cancelarSemCorpoUsaMotivoPadrao() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(3), "doador-" + UUID.randomUUID());

        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.motivo").value("Cancelado pelo doador"));
    }

    @Test
    void cancelarDeNovoResponde409() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(3), "doador-" + UUID.randomUUID());
        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId())).andExpect(status().isOk());

        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId()))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-ja-cancelado"));

        // a vaga foi devolvida uma vez só
        assertThat(slots.findById(ag.getSlot().getId()).orElseThrow().getVagasOcupadas()).isZero();
    }

    @Test
    void compensadoPelaSagaNaoTemCancelarETem409() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CANCELADO_COMPENSACAO_SAGA, Duration.ofDays(3),
                "doador-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos/{id}", ag.getId()))
                .andExpect(jsonPath("$._links.cancelar").doesNotExist())
                .andExpect(jsonPath("$._links.novo-agendamento").exists());
        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId()))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-ja-cancelado"));
    }

    @Test
    void provisorioNaoTemLinkDeAcaoENaoPodeSerCancelado() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CRIADO_PROVISORIO, Duration.ofDays(3), "doador-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos/{id}", ag.getId()))
                .andExpect(jsonPath("$._links.self").exists())
                .andExpect(jsonPath("$._links.cancelar").doesNotExist())
                .andExpect(jsonPath("$._links.novo-agendamento").doesNotExist());
        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId()))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-nao-cancelavel"));
    }

    @Test
    void menosDeDuasHorasAntesNaoPodeCancelar() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofMinutes(90), "doador-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos/{id}", ag.getId()))
                .andExpect(jsonPath("$._links.cancelar").doesNotExist());
        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", ag.getId()))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:prazo-cancelamento-expirado"));
    }

    @Test
    void confirmadoNoPassadoEConcluidoESemAcoes() throws Exception {
        Agendamento ag = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(-1), "doador-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos/{id}", ag.getId()))
                .andExpect(jsonPath("$.concluido").value(true))
                .andExpect(jsonPath("$._links.cancelar").doesNotExist())
                .andExpect(jsonPath("$._links.novo-agendamento").doesNotExist());
    }

    @Test
    void inexistenteResponde404() throws Exception {
        mockMvc.perform(get("/api/v1/agendamentos/{id}", "nao-existe"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-nao-encontrado"));
        mockMvc.perform(post("/api/v1/agendamentos/{id}/cancelamento", "nao-existe"))
                .andExpect(status().isNotFound());
    }

    @Test
    void listaSoOsAgendamentosDoDoadorDoMaisRecenteParaOMaisAntigo() throws Exception {
        String doador = "doador-" + UUID.randomUUID();
        Agendamento antigo = criar(StatusAgendamento.CANCELADO_DOADOR, Duration.ofDays(2), doador);
        Agendamento recente = criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(5), doador);
        criar(StatusAgendamento.CONFIRMADO, Duration.ofDays(5), "outro-" + UUID.randomUUID());

        mockMvc.perform(get("/api/v1/agendamentos").param("doadorId", doador))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.itens", hasSize(2)))
                .andExpect(jsonPath("$.itens[0].id").value(recente.getId()))
                .andExpect(jsonPath("$.itens[0]._links.cancelar").exists())
                .andExpect(jsonPath("$.itens[1].id").value(antigo.getId()))
                .andExpect(jsonPath("$.itens[1]._links.cancelar").doesNotExist());
    }

    @Test
    void listarSemDoadorResponde400() throws Exception {
        mockMvc.perform(get("/api/v1/agendamentos"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.type").value("urn:startech:error:requisicao-invalida"));
    }

    private Agendamento criar(StatusAgendamento status, Duration daquiA, String doadorId) {
        Instant inicio = Instant.now().plus(daquiA);
        boolean ocupa = !status.cancelado();
        Slot slot = slots.save(new Slot("slot-" + UUID.randomUUID(), "posto-1", inicio,
                inicio.plus(Duration.ofMinutes(20)), 2, ocupa ? 1 : 0));
        return agendamentos.save(new Agendamento("ag-" + UUID.randomUUID(), doadorId, slot, status));
    }
}
