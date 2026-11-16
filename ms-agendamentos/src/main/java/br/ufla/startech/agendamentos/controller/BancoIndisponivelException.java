package br.ufla.startech.agendamentos.controller;

public class BancoIndisponivelException extends RuntimeException {

    public BancoIndisponivelException(Throwable cause) {
        super(cause);
    }
}
