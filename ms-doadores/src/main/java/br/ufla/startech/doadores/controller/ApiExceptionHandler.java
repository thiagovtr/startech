package br.ufla.startech.doadores.controller;

import java.net.URI;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import br.ufla.startech.doadores.domain.RegraIntervaloDoacao.Violacao;
import br.ufla.startech.doadores.service.DoadorInaptoException;
import br.ufla.startech.doadores.service.DoadorNaoEncontradoException;
import br.ufla.startech.doadores.service.TravaDeOutroDoadorException;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(DoadorNaoEncontradoException.class)
    ProblemDetail handleDoadorNaoEncontrado(DoadorNaoEncontradoException exception) {
        return problem(HttpStatus.NOT_FOUND, "urn:startech:error:doador-nao-encontrado", "Doador não encontrado",
                "Não existe doador cadastrado com o identificador informado.");
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ProblemDetail handleArgumentoInvalido(MethodArgumentTypeMismatchException exception) {
        return problem(HttpStatus.BAD_REQUEST, "urn:startech:error:identificador-invalido", "Identificador inválido",
                "O identificador do doador deve ser um UUID válido.");
    }

    /** RN01: o orquestrador repassa este corpo como a recusa da SAGA, e o app mostra o {@code detail}. */
    @ExceptionHandler(DoadorInaptoException.class)
    ProblemDetail handleDoadorInapto(DoadorInaptoException exception) {
        Violacao violacao = exception.getViolacao();
        ProblemDetail problem = problem(HttpStatus.UNPROCESSABLE_ENTITY,
                "urn:startech:error:intervalo-minimo-nao-cumprido", "Doador inapto para a data escolhida",
                violacao.detalhe());
        problem.setProperty("liberadoAPartirDe", violacao.liberadaAPartirDe().toString());
        problem.setProperty("intervaloDias", violacao.intervaloDias());
        problem.setProperty("invalidParams", List.of(Map.of("name", "dataSlot", "reason", violacao.motivoCampo())));
        return problem;
    }

    @ExceptionHandler(TravaDeOutroDoadorException.class)
    ProblemDetail handleTravaDeOutroDoador(TravaDeOutroDoadorException exception) {
        return problem(HttpStatus.CONFLICT, "urn:startech:error:agendamento-de-outro-doador",
                "Agendamento de outro doador", exception.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ProblemDetail handleCorpoInvalido(MethodArgumentNotValidException exception) {
        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST, "urn:startech:error:requisicao-invalida",
                "Requisição inválida", "Um ou mais campos do corpo são inválidos.");
        problem.setProperty("invalidParams", exception.getBindingResult().getFieldErrors().stream()
                .map(erro -> Map.of("name", erro.getField(), "reason", String.valueOf(erro.getDefaultMessage())))
                .toList());
        return problem;
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ProblemDetail handleCorpoIlegivel(HttpMessageNotReadableException exception) {
        return problem(HttpStatus.BAD_REQUEST, "urn:startech:error:requisicao-invalida", "Requisição inválida",
                "O corpo da requisição não é um JSON válido ou tem campos em formato errado.");
    }

    @ExceptionHandler(BancoIndisponivelException.class)
    ProblemDetail handleBancoIndisponivel(BancoIndisponivelException exception) {
        return problem(HttpStatus.SERVICE_UNAVAILABLE, "urn:startech:error:banco-indisponivel", "Banco indisponível",
                "O banco de dados não está disponível no momento.");
    }

    private ProblemDetail problem(HttpStatus status, String type, String title, String detail) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setType(URI.create(type));
        problem.setTitle(title);
        return problem;
    }
}
