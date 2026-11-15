package br.ufla.startech.doadores.controller;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class HealthControllerTest {

    private final StubJdbcTemplate jdbcTemplate = new StubJdbcTemplate();
    private final MockMvc mockMvc = MockMvcBuilders
            .standaloneSetup(new HealthController(jdbcTemplate))
            .setControllerAdvice(new ApiExceptionHandler())
            .build();

    @Test
    void healthReturnsServiceStatus() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(jsonPath("$.servico").value("ms-doadores"));
    }

    @Test
    void readyReturnsServiceStatus() throws Exception {
        jdbcTemplate.indisponivel = false;

        mockMvc.perform(get("/ready"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"))
                .andExpect(jsonPath("$.servico").value("ms-doadores"));
    }

    @Test
    void readyReturnsServiceUnavailableWhenDatabaseIsDown() throws Exception {
        jdbcTemplate.indisponivel = true;

        mockMvc.perform(get("/ready"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.type").value("urn:startech:error:banco-indisponivel"));
    }

    private static class StubJdbcTemplate extends JdbcTemplate {
        private boolean indisponivel;

        @Override
        public <T> T queryForObject(String sql, Class<T> requiredType) {
            if (indisponivel) {
                throw new DataAccessResourceFailureException("PostgreSQL indisponível");
            }
            return requiredType.cast(1);
        }
    }
}
