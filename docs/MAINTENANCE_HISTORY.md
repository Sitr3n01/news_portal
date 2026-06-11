# Histórico de Manutenção

> Este documento substitui os antigos roadmaps e cronogramas de desenvolvimento. Como o sistema encontra-se em produção, aqui devem ser registrados apenas os pacotes de manutenção, auditorias de segurança e grandes atualizações realizadas.

---

## [2026-06-11] Reestruturação da Documentação

- **Descrição**: Reestruturação completa da árvore de documentação do projeto.
- **Camadas Criadas**:
  - `docs/user/`: Documentação *User Friendly* com foco nos usuários finais não-técnicos (arquivos Markdown e HTML). Inclui manuais detalhados do admin, publicações, newsletter e redes sociais.
  - `docs/technical/`: Documentação técnica focada em engenharia de software, separada por assuntos (Segurança, Deploy, Guias e Arquitetura).
  - `docs/ai/`: Regras e visões sistêmicas estritas para o auxílio de IA no projeto.
- **Limpeza**: Remoção completa de arquivos de logs de conversas, `roadmap.md` e similares. Arquivos de instrução de agentes na raiz foram completamente limpos de acordo com as restrições atuais do sistema.
