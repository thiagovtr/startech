package br.ufla.startech.doadores.service;

import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import br.ufla.startech.doadores.domain.Doador;
import br.ufla.startech.doadores.dto.DoadorPerfilRequest;
import br.ufla.startech.doadores.dto.DoadorPerfilResponse;
import br.ufla.startech.doadores.repository.DoadorRepository;

@Service
public class DoadorService {

    private final DoadorRepository doadorRepository;

    public DoadorService(DoadorRepository doadorRepository) {
        this.doadorRepository = doadorRepository;
    }

    @Transactional(readOnly = true)
    public DoadorPerfilResponse buscarPerfil(UUID id) {
        return doadorRepository.findById(id)
                .map(this::paraResponse)
                .orElseThrow(() -> new DoadorNaoEncontradoException(id));
    }

    @Transactional
    public DoadorPerfilResponse salvarPerfil(UUID id, DoadorPerfilRequest request) {
        Doador doador = doadorRepository.findById(id)
                .map(existente -> {
                    existente.atualizarPerfil(
                            request.nome(), request.tipoSanguineo(), request.sexo(), request.dataUltimaDoacao()
                    );
                    return existente;
                })
                .orElseGet(() -> new Doador(
                        id, request.nome(), request.tipoSanguineo(), request.sexo(), request.dataUltimaDoacao()
                ));
        return paraResponse(doadorRepository.save(doador));
    }

    private DoadorPerfilResponse paraResponse(Doador doador) {
        return new DoadorPerfilResponse(
                doador.getId(),
                doador.getNome(),
                doador.getTipoSanguineo(),
                doador.getSexo().name(),
                doador.getDataUltimaDoacao()
        );
    }
}
