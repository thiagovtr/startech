package br.ufla.startech.agendamentos.service;

public class AgendamentoNaoEncontradoException extends RuntimeException {

    public AgendamentoNaoEncontradoException(String id) {
        super("Não existe agendamento com o identificador " + id + ".");
    }
}
