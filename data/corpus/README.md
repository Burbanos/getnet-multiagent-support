# Corpus de Conhecimento Oficial Getnet

Este diretório contém o corpus de documentos oficiais coletados para a base de conhecimento do assistente multiagente Getnet.

## Origem e Fontes

Os dados são obtidos a partir dos domínios oficiais listados em `data/sources.yaml`:
- **getnet.net/en**: Conteúdo global institucional, soluções de pagamento presencial, e-commerce, omnichannel e APIs para desenvolvedores.
- **site.getnet.com.br**: Conteúdo oficial para o mercado brasileiro (Getnet Brasil), abrangendo maquininhas, Pix, taxas, antecipação e manuais operacionais. O domínio `www.santander.com.br` foi removido porque sua CDN (Akamai) bloqueia o User-Agent do projeto com HTTP 403 no `robots.txt`; já o `site.getnet.com.br` não possui `robots.txt` (retorna HTTP 404), o que pela RFC 9309 indica ausência de restrições de rastreamento.

> **Nota de Mercado**: O caminho `getnet.net/pt` é expressamente excluído da coleta por pertencer ao mercado de Portugal.

## Coleta Ética e Conformidade

A coleta é realizada de forma estritamente ética pelo módulo `src/rag/ingest.py`:
- Consulta e respeita integralmente as diretivas de cada `robots.txt` antes de qualquer requisição.
- Aplica intervalo mínimo de requisições por host para não sobrecarregar os servidores.
- Identifica-se publicamente com o `User-Agent`:
  `getnet-multiagent-support-ingest/1.0 (+https://github.com/Burbanos/getnet-multiagent-support)`.

## Como Regenerar o Corpus

Para executar a ingestão e atualizar os arquivos `pages.jsonl` e `manifest.json`:

```bash
python -m src.rag.ingest
```

## Data da Coleta
- **Data de geração**: 06/11/2026.

## Aviso Legal e Atribuição

Este conteúdo pertence aos respectivos titulares e não está coberto pela licença deste repositório. Ele é usado apenas para fins de avaliação técnica e será removido mediante solicitação.
