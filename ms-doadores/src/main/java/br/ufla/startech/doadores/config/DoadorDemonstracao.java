package br.ufla.startech.doadores.config;

import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.doadores.repository.DoadorRepository;

/**
 * Estado do doador de teste para a demonstração e os E2E (perfil {@code demo}, ligado no compose.yaml).
 *
 * <p>A cada subida, o {@code doador1} (homem, intervalo de 60 dias) fica com a última doação há 10 dias, relativa à
 * data da subida, como a grade do {@code ms-agendamentos}. Assim ele fica apto para os {@code slot-futuro*} (90+
 * dias) e inapto para o {@code slot-proximo} (7 dias). As travas não são apagadas aqui: o
 * {@code scripts/demo/preparar.sh} as zera junto com os agendamentos.
 */
@Component
@Profile("demo")
public class DoadorDemonstracao implements ApplicationRunner {

    static final UUID DOADOR1 = UUID.fromString("11111111-1111-1111-1111-111111111111");
    private static final Logger LOG = LoggerFactory.getLogger(DoadorDemonstracao.class);

    private final DoadorRepository doadores;
    private final Clock clock;

    public DoadorDemonstracao(DoadorRepository doadores, Clock clock) {
        this.doadores = doadores;
        this.clock = clock;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        LocalDate ultimaDoacao = LocalDate.ofInstant(clock.instant(), ZoneOffset.UTC).minusDays(10);
        doadores.findById(DOADOR1).ifPresent(doador -> {
            doador.registrarDoacao(ultimaDoacao);
            LOG.info("doador de demonstração: última doação em {}", ultimaDoacao);
        });
    }
}
