package br.ufla.startech.agendamentos.service;

/** O agendamento existe, mas o estado atual não permite cancelá-lo (409 Conflict). */
public class CancelamentoRecusadoException extends RuntimeException {

    private final String tipo;
    private final String titulo;

    public CancelamentoRecusadoException(String tipo, String titulo, String detalhe) {
        super(detalhe);
        this.tipo = tipo;
        this.titulo = titulo;
    }

    public String getTipo() {
        return tipo;
    }

    public String getTitulo() {
        return titulo;
    }
}
