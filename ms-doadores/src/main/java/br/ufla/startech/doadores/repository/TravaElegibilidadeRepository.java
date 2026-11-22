package br.ufla.startech.doadores.repository;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

import br.ufla.startech.doadores.domain.TravaElegibilidade;

public interface TravaElegibilidadeRepository extends JpaRepository<TravaElegibilidade, String> {

    List<TravaElegibilidade> findByDoadorId(UUID doadorId);
}
