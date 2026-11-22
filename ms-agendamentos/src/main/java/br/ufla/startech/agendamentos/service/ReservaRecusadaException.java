package br.ufla.startech.agendamentos.service;

import org.springframework.http.HttpStatus;

/** Recusa de negócio num passo da SAGA (o orquestrador não tenta de novo: compensa ou recusa). */
public class ReservaRecusadaException extends RuntimeException {

    private final HttpStatus status;
    private final String tipo;
    private final String titulo;

    public ReservaRecusadaException(HttpStatus status, String tipo, String titulo, String detalhe) {
        super(detalhe);
        this.status = status;
        this.tipo = tipo;
        this.titulo = titulo;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getTipo() {
        return tipo;
    }

    public String getTitulo() {
        return titulo;
    }
}
