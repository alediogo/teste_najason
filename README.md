# Desafio Técnico Nasajon - Engenharia de Dados

Solução implementada em **Python** para ingestão, enriquecimento e análise de dados demográficos integrados à API do IBGE.

## 🚀 Como Rodar

1. **Pré-requisitos:** Python 3 instalado.
2. **Instalar dependências:**
   ```bash
   pip install pandas requests

3. **Executar**
    ```bash
   python solucao.py

## 📄 Notas Explicativas
**1. Arquitetura e Decisões de Projeto**
Optei por desenvolver a solução em Python devido à sua robustez na manipulação de dados tabulares (biblioteca pandas) e simplicidade nas requisições HTTP (requests). O código foi estruturado de forma modular, separando responsabilidades de autenticação, ingestão de dados, processamento e envio de métricas.

**2. Estratégia de Enriquecimento de Dados (IBGE)**
Para otimizar a performance e evitar múltiplas chamadas de rede, adotei a estratégia de carregamento total em memória. O script baixa a lista completa de municípios do IBGE uma única vez e cria um dicionário indexado, permitindo busca em tempo constante durante o processamento.

**3. Tratamento de Inconsistências e "Data Quality"**
Durante a análise exploratória, identifiquei desafios de qualidade de dados que exigiram decisões técnicas explícitas:

**Erros de Digitação (Typos):** Registros como Curitba e Belo Horzionte foram tratados. Implementei uma normalização de strings e um mapeamento determinístico para recuperar os IDs corretos, garantindo a integridade dos dados em vez de depender de algoritmos probabilísticos (fuzzy match).

**Problemas de Encoding/Formatação:** O arquivo de entrada apresentava espaços após as vírgulas e variações de encoding. Utilizei parâmetros de limpeza (skipinitialspace=True e Regex) para garantir que a população fosse lida estritamente como numérica.

**Duplicatas Ambíguas ("Santoo Andre"):** Identifiquei um registro duplicado (Santoo Andre) com população divergente do oficial.

**Decisão:** Marquei este registro como AMBIGUO/ERRO.

**Justificativa:** Somar um registro duplicado com dados divergentes enviesaria as estatísticas da região Sudeste. A decisão mais segura para a integridade do relatório foi isolar o dado suspeito.

**4. Conclusão**
A solução prioriza a consistência. O código protege a aplicação contra falhas de API e dados sujos, garantindo que as estatísticas geradas reflitam com precisão os dados válidos processados.
