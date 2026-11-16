package br.ufla.startech.doadores.controller;

import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import br.ufla.startech.doadores.service.DoadorNaoEncontradoException;

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
