package br.ufla.startech.doadores.service;

/** O {@code agendamentoId} já trava a elegibilidade de outro doador: chave reaproveitada com outros dados. */
public class TravaDeOutroDoadorException extends RuntimeException {

    public TravaDeOutroDoadorException(String agendamentoId) {
        super("O agendamento " + agendamentoId + " já está associado a outro doador.");
    }
}
