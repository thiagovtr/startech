package br.ufla.startech.doadores.domain;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Optional;

/**
 * RN01: intervalo mínimo entre doações de sangue total (Portaria de Consolidação MS nº 5/2017, anexo IV): 60 dias
 * para homens e 90 para mulheres, contados da última doação. Regra pura, sem IO.
 */
public final class RegraIntervaloDoacao {

    private static final DateTimeFormatter DATA_BR = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    /** Motivo da recusa, com o texto que o app mostra ao doador. */
    public record Violacao(LocalDate ultimaDoacao, LocalDate liberadaAPartirDe, int intervaloDias,
                           String detalhe, String motivoCampo) {
    }

    private RegraIntervaloDoacao() {
    }

    /** Vazio se o doador pode doar em {@code dataPretendida} ({@code ultimaDoacao} nula: nunca doou). */
    public static Optional<Violacao> avaliar(Sexo sexo, LocalDate ultimaDoacao, LocalDate dataPretendida) {
        if (ultimaDoacao == null) {
            return Optional.empty();
        }
        int intervalo = sexo.getIntervaloDias();
        LocalDate liberacao = ultimaDoacao.plusDays(intervalo);
        if (!dataPretendida.isBefore(liberacao)) {
            return Optional.empty();
        }
        String detalhe = ("A última doação foi em %s. Conforme a Portaria MS nº 5/2017, a próxima doação de sangue "
                + "total é permitida a partir de %s (%d dias de intervalo para o sexo %s).")
                .formatted(DATA_BR.format(ultimaDoacao), DATA_BR.format(liberacao), intervalo, sexo.getDescricao());
        return Optional.of(new Violacao(ultimaDoacao, liberacao, intervalo, detalhe,
                "%s é anterior a %s".formatted(dataPretendida, liberacao)));
    }
}
