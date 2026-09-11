name: Backfill campos restantes

on:
  workflow_dispatch:
    inputs:
      aplicar:
        description: "Gravar alterações no Supabase?"
        required: true
        type: boolean
        default: false

jobs:
  backfill:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout do código
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependências
        run: |
          python -m pip install --upgrade pip
          pip install -r requeriments.txt

      - name: Executar backfill
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          if [ "${{ inputs.aplicar }}" = "true" ]; then
            python backfill_campos_restantes.py --aplicar
          else
            python backfill_campos_restantes.py
          fi
