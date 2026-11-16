package br.ufla.startech.doadores.service;

import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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
                .map(doador -> new DoadorPerfilResponse(doador.getId(), doador.getTipoSanguineo()))
                .orElseThrow(() -> new DoadorNaoEncontradoException(id));
    }
}
