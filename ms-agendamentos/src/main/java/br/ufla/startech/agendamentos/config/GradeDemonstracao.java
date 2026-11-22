package br.ufla.startech.agendamentos.config;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.repository.SlotRepository;

/**
 * Grade de horários da demonstração e dos E2E (perfil {@code demo}, ligado no compose.yaml).
 *
 * <p>As datas são relativas ao momento da subida, para a grade não vencer antes da apresentação. Só cria os slots
 * que ainda não existem (não mexe nas vagas já ocupadas); para recomeçar do zero, use
 * {@code scripts/demo/preparar.sh}. Os ids casam com a regra RN01 da demonstração (última doação do doador1 há
 * 10 dias, intervalo mínimo de 60):
 * <ul>
 *   <li>{@code slot-futuro*}: daqui a 90+ dias, doador apto → SAGA confirmada;</li>
 *   <li>{@code slot-proximo}: daqui a 7 dias, doador inapto (RN01) → SAGA compensada no passo 2;</li>
 *   <li>{@code slot-lotado}: capacidade 0 → SAGA recusada no passo 1 (não aparece na listagem).</li>
 * </ul>
 */
@Component
@Profile("demo")
public class GradeDemonstracao implements ApplicationRunner {

    private static final Logger LOG = LoggerFactory.getLogger(GradeDemonstracao.class);
    private static final Duration DURACAO = Duration.ofMinutes(20);

    private record Horario(String id, String postoId, Duration daquiA, int capacidade) {
    }

    private static final List<Horario> GRADE = List.of(
            new Horario("slot-futuro", "hemominas-lavras", Duration.ofDays(90).plusHours(14), 5),
            new Horario("slot-futuro-2", "hemominas-lavras", Duration.ofDays(91).plusHours(9), 5),
            new Horario("slot-futuro-3", "ufla-campus", Duration.ofDays(95).plusHours(10), 3),
            new Horario("slot-proximo", "hemominas-lavras", Duration.ofDays(7).plusHours(14), 5),
            new Horario("slot-lotado", "ufla-campus", Duration.ofDays(30).plusHours(15), 0)
    );

    private final SlotRepository slots;
    private final Clock clock;

    public GradeDemonstracao(SlotRepository slots, Clock clock) {
        this.slots = slots;
        this.clock = clock;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        Instant hoje = clock.instant().truncatedTo(ChronoUnit.DAYS);
        int criados = 0;
        for (Horario h : GRADE) {
            if (!slots.existsById(h.id())) {
                Instant inicio = hoje.plus(h.daquiA());
                slots.save(new Slot(h.id(), h.postoId(), inicio, inicio.plus(DURACAO), h.capacidade(), 0));
                criados++;
            }
        }
        LOG.info("grade de demonstração: {} slot(s) criado(s), {} já existiam", criados, GRADE.size() - criados);
    }
}
