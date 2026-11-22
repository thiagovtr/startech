package br.ufla.startech.doadores.service;

import br.ufla.startech.doadores.domain.RegraIntervaloDoacao.Violacao;

/** RN01 violada: vira {@code 422 intervalo-minimo-nao-cumprido}, recusa de negócio que a SAGA compensa. */
public class DoadorInaptoException extends RuntimeException {

    private final transient Violacao violacao;

    public DoadorInaptoException(Violacao violacao) {
        super(violacao.detalhe());
        this.violacao = violacao;
    }

    public Violacao getViolacao() {
        return violacao;
    }
}
