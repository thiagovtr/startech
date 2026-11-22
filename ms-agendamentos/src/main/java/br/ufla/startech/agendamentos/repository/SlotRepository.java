package br.ufla.startech.agendamentos.repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import br.ufla.startech.agendamentos.domain.Slot;

public interface SlotRepository extends JpaRepository<Slot, String> {

    /** Trava a linha do slot: duas reservas simultâneas na última vaga não passam as duas. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Slot s WHERE s.id = :id")
    Optional<Slot> buscarParaAtualizacao(@Param("id") String id);

    /** Slots que começam no intervalo e ainda têm vaga, do mais próximo para o mais distante. */
    @Query("""
            SELECT s FROM Slot s
            WHERE s.dataHoraInicio > :de AND s.dataHoraInicio <= :ate
              AND s.vagasOcupadas < s.capacidade
              AND (:postoId IS NULL OR s.postoId = :postoId)
            ORDER BY s.dataHoraInicio, s.id
            """)
    List<Slot> listarDisponiveis(@Param("postoId") String postoId, @Param("de") Instant de, @Param("ate") Instant ate);
}
