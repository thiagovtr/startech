package br.ufla.startech.doadores.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import br.ufla.startech.doadores.repository.TravaElegibilidadeRepository;

/** Passo 2 da SAGA (RN01 e trava) e sua compensação, contra um PostgreSQL real, com o doador1 do perfil demo. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("demo")
@Testcontainers(disabledWithoutDocker = true)
class ElegibilidadeControllerTests {

    private static final String DOADOR1 = "11111111-1111-1111-1111-111111111111";

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
    private TravaElegibilidadeRepository travas;

    @Autowired
    private JdbcTemplate jdbc;

    @BeforeEach
    void limparTravas() {
        travas.deleteAll();
    }

    @Test
    void perfilDemoDeixaODoador1ComDoacaoHaDezDias() {
        LocalDate ultima = jdbc.queryForObject(
                "SELECT data_ultima_doacao FROM doadores WHERE id = ?::uuid", LocalDate.class, DOADOR1);
        assertThat(ultima).isEqualTo(LocalDate.now(ZoneOffset.UTC).minusDays(10));
    }

    @Test
    void doadorAptoRecebeATrava() throws Exception {
        String ag = id();
        Instant data = daquiA(90);

        reservar(DOADOR1, ag, data, "saga-1-step2")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.doadorId").value(DOADOR1))
                .andExpect(jsonPath("$.agendamentoId").value(ag))
                .andExpect(jsonPath("$.dataSlot").value(data.toString()))
                .andExpect(jsonPath("$.travado").value(true));

        assertThat(travas.findById(ag)).isPresent();
    }

    @Test
    void doadorInaptoRecebe422ComMotivoDaPortaria() throws Exception {
        String ag = id();
        LocalDate liberacao = LocalDate.now(ZoneOffset.UTC).plusDays(50);

        reservar(DOADOR1, ag, daquiA(7), "saga-2-step2")
                .andExpect(status().isUnprocessableEntity())
                .andExpect(content().contentTypeCompatibleWith("application/problem+json"))
                .andExpect(jsonPath("$.type").value("urn:startech:error:intervalo-minimo-nao-cumprido"))
                .andExpect(jsonPath("$.status").value(422))
                .andExpect(jsonPath("$.detail").value(org.hamcrest.Matchers.containsString("Portaria MS nº 5/2017")))
                .andExpect(jsonPath("$.liberadoAPartirDe").value(liberacao.toString()))
                .andExpect(jsonPath("$.intervaloDias").value(60))
                .andExpect(jsonPath("$.invalidParams[0].name").value("dataSlot"));

        assertThat(travas.findById(ag)).isEmpty();
    }

    @Test
    void repetirAReservaDevolveAMesmaTrava() throws Exception {
        String ag = id();
        Instant data = daquiA(90);

        reservar(DOADOR1, ag, data, "saga-3-step2").andExpect(status().isOk());
        reservar(DOADOR1, ag, data, "saga-3-step2")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.agendamentoId").value(ag));

        assertThat(travas.findByDoadorId(UUID.fromString(DOADOR1))).hasSize(1);
    }

    @Test
    void outraSagaDoMesmoDoadorNaoEBarradaPelaTrava() throws Exception {
        // A RN09 (passo 1) é quem impede duas SAGAs ativas; a trava não entra na RN01.
        reservar(DOADOR1, id(), daquiA(90), "saga-4-step2").andExpect(status().isOk());
        reservar(DOADOR1, id(), daquiA(91), "saga-5-step2").andExpect(status().isOk());
    }

    @Test
    void compensacaoRemoveATravaEEIdempotente() throws Exception {
        String ag = id();
        reservar(DOADOR1, ag, daquiA(90), "saga-7-step2").andExpect(status().isOk());

        liberar(DOADOR1, ag).andExpect(status().isNoContent());
        assertThat(travas.findById(ag)).isEmpty();
        liberar(DOADOR1, ag).andExpect(status().isNoContent());

    }

    @Test
    void compensacaoDeOutroDoadorNaoRemoveATrava() throws Exception {
        String ag = id();
        reservar(DOADOR1, ag, daquiA(90), "saga-9-step2").andExpect(status().isOk());

        liberar(UUID.randomUUID().toString(), ag).andExpect(status().isNoContent());
        assertThat(travas.findById(ag)).isPresent();
    }

    @Test
    void agendamentoReaproveitadoPorOutroDoadorDa409() throws Exception {
        String ag = id();
        String outro = criarDoador();
        reservar(DOADOR1, ag, daquiA(90), "saga-10-step2").andExpect(status().isOk());

        reservar(outro, ag, daquiA(90), "saga-10-step2")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.type").value("urn:startech:error:agendamento-de-outro-doador"));
    }

    @Test
    void doadorInexistenteDa404() throws Exception {
        reservar(UUID.randomUUID().toString(), id(), daquiA(90), "saga-11-step2")
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("urn:startech:error:doador-nao-encontrado"));
    }

    @Test
    void corpoSemDataDa400() throws Exception {
        mockMvc.perform(post("/api/v1/doadores/{id}/reservas-elegibilidade", DOADOR1)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"agendamentoId\":\"" + id() + "\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.type").value("urn:startech:error:requisicao-invalida"))
                .andExpect(jsonPath("$.invalidParams[0].name").value("dataSlot"));
    }

    @Test
    void repeticoesConcorrentesCriamUmaSoTrava() throws Exception {
        int pedidos = 6;
        String ag = id();
        Instant data = daquiA(90);
        ExecutorService pool = Executors.newFixedThreadPool(pedidos);
        CountDownLatch largada = new CountDownLatch(1);
        List<Future<Integer>> resultados = new ArrayList<>();
        for (int i = 0; i < pedidos; i++) {
            Callable<Integer> pedido = () -> {
                largada.await();
                return reservar(DOADOR1, ag, data, "saga-c-step2").andReturn().getResponse().getStatus();
            };
            resultados.add(pool.submit(pedido));
        }
        largada.countDown();
        List<Integer> status = new ArrayList<>();
        for (Future<Integer> resultado : resultados) {
            status.add(resultado.get());
        }
        pool.shutdown();

        assertThat(status).containsOnly(200);
        assertThat(travas.findByDoadorId(UUID.fromString(DOADOR1))).hasSize(1);
    }

    private ResultActions reservar(String doador, String agendamento, Instant data, String chave) throws Exception {
        return mockMvc.perform(post("/api/v1/doadores/{id}/reservas-elegibilidade", doador)
                .header("Idempotency-Key", chave)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"agendamentoId\":\"%s\",\"dataSlot\":\"%s\"}".formatted(agendamento, data)));
    }

    private ResultActions liberar(String doador, String agendamento) throws Exception {
        return mockMvc.perform(delete("/api/v1/doadores/{id}/reservas-elegibilidade/{ag}", doador, agendamento)
                .header("Idempotency-Key", "saga-x-step2-comp"));
    }

    private String criarDoador() {
        UUID id = UUID.randomUUID();
        jdbc.update("INSERT INTO doadores (id, tipo_sanguineo, sexo) VALUES (?, 'A+', 'F')", id);
        return id.toString();
    }

    private static Instant daquiA(int dias) {
        return LocalDate.now(ZoneOffset.UTC).atStartOfDay().toInstant(ZoneOffset.UTC)
                .plus(Duration.ofDays(dias).plusHours(14));
    }

    private static String id() {
        return UUID.randomUUID().toString();
    }
}
