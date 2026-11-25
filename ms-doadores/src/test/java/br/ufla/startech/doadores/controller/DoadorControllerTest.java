package br.ufla.startech.doadores.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.LocalDate;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import br.ufla.startech.doadores.dto.DoadorPerfilResponse;
import br.ufla.startech.doadores.service.DoadorNaoEncontradoException;
import br.ufla.startech.doadores.service.DoadorService;

class DoadorControllerTest {

    private static final UUID DOADOR_ID = UUID.fromString("11111111-1111-1111-1111-111111111111");

    private final StubDoadorService doadorService = new StubDoadorService();
    private final MockMvc mockMvc = MockMvcBuilders
            .standaloneSetup(new DoadorController(doadorService))
            .setControllerAdvice(new ApiExceptionHandler())
            .build();

    @Test
    void buscaPerfilRetornaApenasCamposPublicos() throws Exception {
        doadorService.resposta = new DoadorPerfilResponse(
                DOADOR_ID, "Doador StarTech", "O-", "M", LocalDate.of(2026, 11, 14)
        );

        mockMvc.perform(get("/api/v1/doadores/{id}", DOADOR_ID))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(DOADOR_ID.toString()))
                .andExpect(jsonPath("$.nome").value("Doador StarTech"))
                .andExpect(jsonPath("$.tipoSanguineo").value("O-"))
                .andExpect(jsonPath("$.sexo").value("M"))
                .andExpect(jsonPath("$.dataUltimaDoacao").value("2026-11-14"))
                .andExpect(jsonPath("$.cpf").doesNotExist());
    }

    @Test
    void buscaPerfilInexistenteRetornaProblemDetail() throws Exception {
        UUID idInexistente = UUID.randomUUID();
        doadorService.erro = new DoadorNaoEncontradoException(idInexistente);

        mockMvc.perform(get("/api/v1/doadores/{id}", idInexistente))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith("application/problem+json"))
                .andExpect(jsonPath("$.type").value("urn:startech:error:doador-nao-encontrado"))
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void buscaPerfilComUuidInvalidoRetornaProblemDetail() throws Exception {
        mockMvc.perform(get("/api/v1/doadores/nao-e-um-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentTypeCompatibleWith("application/problem+json"))
                .andExpect(jsonPath("$.type").value("urn:startech:error:identificador-invalido"))
                .andExpect(jsonPath("$.status").value(400));
    }

    private static class StubDoadorService extends DoadorService {
        private DoadorPerfilResponse resposta;
        private RuntimeException erro;

        StubDoadorService() {
            super(null);
        }

        @Override
        public DoadorPerfilResponse buscarPerfil(UUID id) {
            if (erro != null) {
                throw erro;
            }
            return resposta;
        }
    }
}
