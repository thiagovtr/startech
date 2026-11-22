package br.ufla.startech.doadores.repository;

import java.util.Optional;
import java.util.UUID;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;

import br.ufla.startech.doadores.domain.Doador;

public interface DoadorRepository extends JpaRepository<Doador, UUID> {

    /** Serializa os pedidos do mesmo doador (uma repetição concorrente não cria a trava duas vezes). */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select d from Doador d where d.id = :id")
    Optional<Doador> buscarParaAtualizacao(UUID id);
}
