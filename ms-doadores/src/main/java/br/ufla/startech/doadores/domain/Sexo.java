package br.ufla.startech.doadores.domain;

/** Sexo biológico, que define o intervalo mínimo entre doações (RN01). */
public enum Sexo {
    M("masculino", 60),
    F("feminino", 90);

    private final String descricao;
    private final int intervaloDias;

    Sexo(String descricao, int intervaloDias) {
        this.descricao = descricao;
        this.intervaloDias = intervaloDias;
    }

    public String getDescricao() {
        return descricao;
    }

    public int getIntervaloDias() {
        return intervaloDias;
    }
}
