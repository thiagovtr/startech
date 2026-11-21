package br.ufla.startech.agendamentos.controller;

import java.net.URI;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import br.ufla.startech.agendamentos.service.AgendamentoNaoEncontradoException;
import br.ufla.startech.agendamentos.service.CancelamentoRecusadoException;
import br.ufla.startech.agendamentos.service.ReservaRecusadaException;

/** Erros em RFC 7807 ({@code application/problem+json}) com tipos {@code urn:startech:error:*}. */
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(BancoIndisponivelException.class)
    ProblemDetail handleBancoIndisponivel(BancoIndisponivelException exception) {
        return problema(HttpStatus.SERVICE_UNAVAILABLE, "banco-indisponivel", "Banco indisponível",
                "O banco de dados não está disponível no momento.");
    }

    @ExceptionHandler(AgendamentoNaoEncontradoException.class)
    ProblemDetail handleNaoEncontrado(AgendamentoNaoEncontradoException exception) {
        return problema(HttpStatus.NOT_FOUND, "agendamento-nao-encontrado", "Agendamento não encontrado",
                exception.getMessage());
    }

    @ExceptionHandler(CancelamentoRecusadoException.class)
    ProblemDetail handleCancelamentoRecusado(CancelamentoRecusadoException exception) {
        return problema(HttpStatus.CONFLICT, exception.getTipo(), exception.getTitulo(), exception.getMessage());
    }

    @ExceptionHandler(ReservaRecusadaException.class)
    ProblemDetail handleReservaRecusada(ReservaRecusadaException exception) {
        return problema(exception.getStatus(), exception.getTipo(), exception.getTitulo(), exception.getMessage());
    }

    /** Só o índice parcial de agendamento ativo (RN09) chega aqui, numa corrida entre duas SAGAs do doador. */
    @ExceptionHandler(DataIntegrityViolationException.class)
    ProblemDetail handleIntegridade(DataIntegrityViolationException exception) {
        return problema(HttpStatus.CONFLICT, "agendamento-ativo", "Agendamento ativo",
                "O doador já possui um agendamento em andamento ou confirmado (RN09).");
    }

    @ExceptionHandler(OptimisticLockingFailureException.class)
    ProblemDetail handleConcorrencia(OptimisticLockingFailureException exception) {
        return problema(HttpStatus.CONFLICT, "conflito-concorrencia", "Conflito de atualização",
                "O agendamento foi alterado ao mesmo tempo por outra operação. Tente novamente.");
    }

    @ExceptionHandler({MissingServletRequestParameterException.class, MethodArgumentNotValidException.class,
            org.springframework.http.converter.HttpMessageNotReadableException.class,
            org.springframework.web.method.annotation.MethodArgumentTypeMismatchException.class})
    ProblemDetail handleRequisicaoInvalida(Exception exception) {
        return problema(HttpStatus.BAD_REQUEST, "requisicao-invalida", "Requisição inválida", exception.getMessage());
    }

    private static ProblemDetail problema(HttpStatus status, String tipo, String titulo, String detalhe) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detalhe);
        problem.setType(URI.create("urn:startech:error:" + tipo));
        problem.setTitle(titulo);
        return problem;
    }
}
