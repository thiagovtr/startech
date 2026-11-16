package br.ufla.startech.agendamentos.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import br.ufla.startech.agendamentos.domain.Agendamento;

public interface AgendamentoRepository extends JpaRepository<Agendamento, String> {
}
