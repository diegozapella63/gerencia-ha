# PDFs com senha (inventados)

Faturas de mentira (Banco Azul, Mercado Bom, Farmácia Sol) para os testes do `pdfsenha.py`, cifradas com o `qpdf`:

| Arquivo | Cifra | Senha de abrir | Senha do dono |
|---|---|---|---|
| `fatura-azul.pdf` | sem senha | | |
| `fatura-aes256.pdf` | AES de 256 bits (R6, a das faturas de hoje) | `12345` | `dono789` |
| `fatura-aes128-objstm.pdf` | AES de 128 bits (R4), com object streams | `12345` | `dono789` |
| `fatura-rc4-128.pdf` | RC4 de 128 bits (R3) | `12345` | `dono789` |
| `fatura-rc4-40.pdf` | RC4 de 40 bits (R2) | `12345` | `dono789` |
| `fatura-so-dono.pdf` | AES de 256 bits, só com a senha do dono (abre sem digitar nada) | (vazia) | `dono789` |

Para refazer: `qpdf --encrypt 12345 dono789 256 -- fatura-azul.pdf fatura-aes256.pdf` (e os outros com `128 --use-aes=y`,
`--object-streams=generate`, `--allow-weak-crypto ... 128 --use-aes=n` e `... 40`).
