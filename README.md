# Power BI Launcher

Launcher simples em Python + PySide6 que reúne os links dos teus dashboards Power BI num só sítio e abre-os com um clique, com um chat integrado para sugestões de melhoria e reporte de erros. O acesso a cada dashboard continua a ser controlado pelo Power BI.

## Como correr

```
pip3 install PySide6
cp dados/dashboards.exemplo.json dados/dashboards.json
python3 app.py
```

O segundo comando cria o teu ficheiro de dashboards a partir do exemplo. Edita-o com os teus links antes de abrir a app.

## Onde ficam os dados

A app guarda tudo em ficheiros JSON, dentro de uma pasta `dados/`:

- `dashboards.json`: a lista de dashboards que aparecem nos cards (tu crias e editas).
- `feedback.json`: o feedback enviado pelo chat (é criado automaticamente).

Se `dashboards.json` não existir, a app mostra um aviso a pedir para o configurares.

### Exemplo de `dashboards.json`

```json
[
  {"nome": "Vendas", "url": "https://app.powerbi.com/...", "emoji": "📈", "data": "2026-10-20"},
  {"nome": "Stock",  "url": "https://app.powerbi.com/...", "emoji": "📦"}
]
```

Cada dashboard tem `nome` e `url` (obrigatórios), e `emoji` e `data` (opcionais, formato AAAA-MM-DD).

## Permissões e acessos

O launcher não gere permissões. Cada card é só um atalho que abre o link do dashboard no browser, e quem controla o acesso é o próprio Power BI.

Quando alguém clica num card, o Power BI verifica na página web se essa pessoa tem permissão para ver o relatório. Se tiver, o dashboard abre. Se não tiver, o Power BI bloqueia o acesso e mostra a mensagem de permissão negada.

Isto significa que:

- Não é preciso configurar utilizadores nem permissões na app.
- Ter o launcher não dá acesso a nada que a pessoa não pudesse ver antes.
- Para dar ou retirar acesso a um dashboard, altera-se a partilha no Power BI (workspace, relatório ou app), não o `dashboards.json`.
- O `dashboards.json` só guarda os links, não guarda dados dos relatórios nem credenciais.

## Usar num servidor interno (recomendado)

Por defeito os ficheiros ficam na pasta `dados/` ao lado do `app.py`, ou seja, cada pessoa tem o seu feedback local, espalhado pelos vários computadores.

Para uma utilização em equipa, o recomendado é colocar a pasta de dados num servidor interno da empresa e indicar o caminho com a variável de ambiente `LAUNCHER_DADOS`. Isto torna a solução mais segura e mais fácil de gerir:

- **Controlo de acesso:** as permissões da pasta no servidor definem quem pode ler e quem pode editar. Por exemplo, todos podem ler o `dashboards.json`, mas só a equipa de TI o pode alterar.
- **Dados dentro da rede:** o feedback (que inclui emails) fica guardado no servidor interno e não em cópias soltas nos computadores dos utilizadores.
- **Um só sítio para manter:** editas o `dashboards.json` uma vez e todos veem a mudança.
- **Cópias de segurança:** a pasta passa a fazer parte do backup normal do servidor.

Mac / Linux:
```
export LAUNCHER_DADOS="/Volumes/Partilha/launcher"
python3 app.py
```

Windows (PowerShell):
```
$env:LAUNCHER_DADOS = "\\servidor\partilha\launcher"
python app.py
```

Nota: a segurança vem das permissões do servidor, não da app. O launcher não faz autenticação própria.

## Limitações

- O feedback fica num ficheiro de texto. Se duas pessoas enviarem ao mesmo tempo, uma pode sobrepor a outra (para uso pequeno chega; para mais, o próximo passo seria uma base de dados).
- Apagar feedback pede o email usado no envio, mas isto não é segurança a sério, é só confirmação.