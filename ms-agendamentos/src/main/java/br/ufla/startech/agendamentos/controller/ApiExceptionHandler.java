package br.ufla.startech.agendamentos.controller;

import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(BancoIndisponivelException.class)
    ProblemDetail handleBancoIndisponivel(BancoIndisponivelException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "O banco de dados não está disponível no momento."
        );
        problem.setType(URI.create("urn:startech:error:banco-indisponivel"));
        problem.setTitle("Banco indisponível");
        return problem;
    }
}
