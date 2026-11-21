package br.ufla.startech.agendamentos.dto;

import java.util.LinkedHashMap;
import java.util.Map;

import br.ufla.startech.agendamentos.domain.Agendamento;
import br.ufla.startech.agendamentos.domain.Slot;
import br.ufla.startech.agendamentos.domain.StatusAgendamento;
import br.ufla.startech.agendamentos.service.AgendamentoService;

/**
 * Representação HATEOAS do recurso Agendamento (contratos §3): os links de ação dependem do estado.
 *
 * <ul>
 *   <li>{@code self}: sempre;</li>
 *   <li>{@code cancelar}: só em {@code CONFIRMADO} e até 2 horas antes do início;</li>
 *   <li>{@code novo-agendamento}: só depois de cancelado (pelo doador ou pela compensação da SAGA);</li>
 *   <li>{@code CRIADO_PROVISORIO}, confirmado fora do prazo ou concluído: nenhum link de ação.</li>
 * </ul>
 */
public final class AgendamentoRepresentacao {

    public static final String DISCLAIMER = "A confirmação deste agendamento organiza o fluxo no posto e não garante"
            + " a doação. A aptidão final depende da triagem clínica presencial.";

    private AgendamentoRepresentacao() {
    }

    public static Map<String, Object> de(Agendamento agendamento, AgendamentoService regras) {
        String base = "/api/v1/agendamentos/" + agendamento.getId();
        Slot slot = agendamento.getSlot();
        StatusAgendamento status = agendamento.getStatus();

        Map<String, Object> corpo = new LinkedHashMap<>();
        corpo.put("id", agendamento.getId());
        corpo.put("status", status.name());
        corpo.put("concluido", regras.concluido(agendamento));
        corpo.put("doadorId", agendamento.getDoadorId());
        corpo.put("slot", Map.of(
                "slotId", slot.getId(),
                "postoId", slot.getPostoId(),
                "dataHoraInicio", slot.getDataHoraInicio().toString(),
                "dataHoraFim", slot.getDataHoraFim().toString()
        ));

        Map<String, Object> links = new LinkedHashMap<>();
        links.put("self", link(base, "GET", "Consultar dados do agendamento"));
        if (status.cancelado()) {
            corpo.put("dataCancelamento", agendamento.getDataCancelamento() == null
                    ? null : agendamento.getDataCancelamento().toString());
            corpo.put("motivo", agendamento.getMotivoCancelamento());
            corpo.put("slotLiberado", slot.getId());
            links.put("novo-agendamento", link("/api/v1/sagas/agendamento", "POST",
                    "Solicitar um novo agendamento"));
        } else {
            corpo.put("disclaimerLegal", DISCLAIMER);
            if (regras.cancelavel(agendamento)) {
                Map<String, Object> cancelar = link(base + "/cancelamento", "POST",
                        "Efetuar cancelamento e liberar vaga para outros doadores");
                cancelar.put("conditions", "Permitido até "
                        + AgendamentoService.ANTECEDENCIA_MINIMA.toHours() + " horas antes do horário agendado");
                links.put("cancelar", cancelar);
            }
        }
        corpo.put("_links", links);
        return corpo;
    }

    private static Map<String, Object> link(String href, String metodo, String titulo) {
        Map<String, Object> link = new LinkedHashMap<>();
        link.put("href", href);
        link.put("method", metodo);
        link.put("title", titulo);
        return link;
    }
}
