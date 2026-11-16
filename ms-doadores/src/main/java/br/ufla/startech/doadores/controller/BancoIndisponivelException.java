package br.ufla.startech.doadores.controller;

public class BancoIndisponivelException extends RuntimeException {

    public BancoIndisponivelException(Throwable cause) {
        super(cause);
    }
}
