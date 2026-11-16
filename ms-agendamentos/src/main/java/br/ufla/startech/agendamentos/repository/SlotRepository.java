package br.ufla.startech.agendamentos.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import br.ufla.startech.agendamentos.domain.Slot;

public interface SlotRepository extends JpaRepository<Slot, String> {
}
