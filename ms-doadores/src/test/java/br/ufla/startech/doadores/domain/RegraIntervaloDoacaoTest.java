package br.ufla.startech.doadores.domain;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDate;
import org.junit.jupiter.api.Test;

class RegraIntervaloDoacaoTest {

    private static final LocalDate ULTIMA = LocalDate.of(2026, 9, 15);

    @Test
    void homemFicaAptoExatamenteNoSexagesimoDia() {
        assertThat(RegraIntervaloDoacao.avaliar(Sexo.M, ULTIMA, ULTIMA.plusDays(60))).isEmpty();

        var violacao = RegraIntervaloDoacao.avaliar(Sexo.M, ULTIMA, ULTIMA.plusDays(59)).orElseThrow();
        assertThat(violacao.liberadaAPartirDe()).isEqualTo(LocalDate.of(2026, 11, 14));
        assertThat(violacao.intervaloDias()).isEqualTo(60);
        assertThat(violacao.detalhe()).isEqualTo("A última doação foi em 15/09/2026. Conforme a Portaria MS nº "
                + "5/2017, a próxima doação de sangue total é permitida a partir de 14/11/2026 (60 dias de intervalo "
                + "para o sexo masculino).");
        assertThat(violacao.motivoCampo()).isEqualTo("2026-11-13 é anterior a 2026-11-14");
    }

    @Test
    void mulherPrecisaDeNoventaDias() {
        assertThat(RegraIntervaloDoacao.avaliar(Sexo.F, ULTIMA, ULTIMA.plusDays(90))).isEmpty();
        var violacao = RegraIntervaloDoacao.avaliar(Sexo.F, ULTIMA, ULTIMA.plusDays(89)).orElseThrow();
        assertThat(violacao.liberadaAPartirDe()).isEqualTo(ULTIMA.plusDays(90));
        assertThat(violacao.detalhe()).contains("90 dias", "feminino");
    }

    @Test
    void dataNoMesmoDiaOuAntesDaUltimaDoacaoEInapta() {
        assertThat(RegraIntervaloDoacao.avaliar(Sexo.M, ULTIMA, ULTIMA)).isPresent();
        assertThat(RegraIntervaloDoacao.avaliar(Sexo.M, ULTIMA, ULTIMA.minusDays(1))).isPresent();
    }

    @Test
    void quemNuncaDoouEstaApto() {
        assertThat(RegraIntervaloDoacao.avaliar(Sexo.F, null, LocalDate.of(2026, 1, 1))).isEmpty();
    }
}
