package br.ufla.startech.doadores.service;

import java.util.UUID;

public class DoadorNaoEncontradoException extends RuntimeException {

    public DoadorNaoEncontradoException(UUID id) {
        super("Doador não encontrado: " + id);
    }
}
