package br.ufla.startech.doadores.repository;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

import br.ufla.startech.doadores.domain.Doador;

public interface DoadorRepository extends JpaRepository<Doador, UUID> {
}
