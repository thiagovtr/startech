package br.ufla.startech.agendamentos;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.repository.AgendamentoRepository;
import br.ufla.startech.agendamentos.repository.SlotRepository;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class MsAgendamentosApplicationTests {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    private SlotRepository slotRepository;

    @Autowired
    private AgendamentoRepository agendamentoRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @DynamicPropertySource
    static void configureDataSource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Test
    void persisteAgendamentoRelacionadoAoSlot() {
        Slot slot = slotRepository.save(slot("slot-relacionamento-" + UUID.randomUUID(), 2, 0));
        Agendamento agendamento = agendamentoRepository.save(new Agendamento(
                "agendamento-" + UUID.randomUUID(),
                "doador-" + UUID.randomUUID(),
                slot,
                StatusAgendamento.CRIADO_PROVISORIO
        ));

        assertThat(agendamentoRepository.findById(agendamento.getId())).isPresent();
    }

    @Test
    void restricoesDeCapacidadeSaoAplicadasPeloPostgreSql() {
        assertThatThrownBy(() -> slotRepository.saveAndFlush(slot("slot-invalido-" + UUID.randomUUID(), 0, 1)))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void indiceParcialImpedeDoisAgendamentosAtivosParaMesmoDoador() {
        String doadorId = "doador-" + UUID.randomUUID();
        Slot primeiroSlot = slotRepository.save(slot("slot-ativo-1-" + UUID.randomUUID(), 1, 0));
        Slot segundoSlot = slotRepository.save(slot("slot-ativo-2-" + UUID.randomUUID(), 1, 0));

        agendamentoRepository.saveAndFlush(new Agendamento(
                "agendamento-ativo-1-" + UUID.randomUUID(), doadorId, primeiroSlot, StatusAgendamento.CONFIRMADO
        ));

        assertThatThrownBy(() -> agendamentoRepository.saveAndFlush(new Agendamento(
                "agendamento-ativo-2-" + UUID.randomUUID(), doadorId, segundoSlot, StatusAgendamento.CRIADO_PROVISORIO
        ))).isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void chaveEstrangeiraImpedeAgendamentoSemSlot() {
        assertThatThrownBy(() -> jdbcTemplate.update(
                "INSERT INTO agendamentos (id, doador_id, slot_id, status) VALUES (?, ?, ?, ?)",
                "agendamento-sem-slot-" + UUID.randomUUID(),
                "doador-" + UUID.randomUUID(),
                "slot-inexistente",
                StatusAgendamento.CONFIRMADO.name()
        )).isInstanceOf(DataIntegrityViolationException.class);
    }

    private Slot slot(String id, int capacidade, int vagasOcupadas) {
        Instant inicio = Instant.now().plus(1, ChronoUnit.DAYS);
        return new Slot(id, "posto-1", inicio, inicio.plus(20, ChronoUnit.MINUTES), capacidade, vagasOcupadas);
    }
}
