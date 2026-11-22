package br.ufla.startech.agendamentos.repository;

import java.util.List;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import br.ufla.startech.agendamentos.domain.Agendamento;

public interface AgendamentoRepository extends JpaRepository<Agendamento, String> {

    @EntityGraph(attributePaths = "slot")
    @Query("SELECT a FROM Agendamento a WHERE a.id = :id")
    Optional<Agendamento> buscarComSlot(@Param("id") String id);

    @EntityGraph(attributePaths = "slot")
    @Query("SELECT a FROM Agendamento a WHERE a.doadorId = :doadorId ORDER BY a.slot.dataHoraInicio DESC")
    List<Agendamento> listarPorDoador(@Param("doadorId") String doadorId);

    @Query("""
            SELECT COUNT(a) > 0 FROM Agendamento a
            WHERE a.doadorId = :doadorId
              AND a.status IN (br.ufla.startech.agendamentos.domain.StatusAgendamento.CRIADO_PROVISORIO,
                               br.ufla.startech.agendamentos.domain.StatusAgendamento.CONFIRMADO)
            """)
    boolean existeAtivoDoDoador(@Param("doadorId") String doadorId);

    /** Trava a linha do agendamento: dois cancelamentos simultâneos não devolvem duas vagas. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM Agendamento a WHERE a.id = :id")
    Optional<Agendamento> buscarParaAtualizacao(@Param("id") String id);
}
