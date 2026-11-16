package br.ufla.startech.doadores;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import br.ufla.startech.doadores.repository.DoadorRepository;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class MsDoadoresApplicationTests {

    private static final String DOADOR_ID = "11111111-1111-1111-1111-111111111111";

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    private DoadorRepository doadorRepository;

    @Autowired
    private MockMvc mockMvc;

    @DynamicPropertySource
    static void configureDataSource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Test
    void migrationCreatesSeedDonorAndProfileIsAvailable() throws Exception {
        var doador = doadorRepository.findById(java.util.UUID.fromString(DOADOR_ID));

        assertThat(doador).isPresent();
        assertThat(doador.orElseThrow().getTipoSanguineo()).isEqualTo("O-");

        mockMvc.perform(get("/api/v1/doadores/{id}", DOADOR_ID))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(DOADOR_ID))
                .andExpect(jsonPath("$.tipoSanguineo").value("O-"));
    }
}
