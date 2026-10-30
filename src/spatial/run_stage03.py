# src/spatial/run_stage03.py
from __future__ import annotations

import logging
import sys
import time

from src.core.settings import DomainSpec, EnvSettings
from src.spatial.cross_validation import run_cross_validation_stage
from src.spatial.empirical_bayes import run_empirical_bayes_stage
from src.spatial.ottobacias import run_ottobacias_stage

logger = logging.getLogger("onco_causal.spatial.stage03")


def run_full_stage03(
    env: EnvSettings | None = None,
    spec: DomainSpec | None = None,
) -> None:
    """Executa a orquestração completa do Stage 03 de Geoprocessamento e Estatística Espacial."""
    env = env or EnvSettings()
    spec = spec or DomainSpec.from_yaml()

    t_start = time.time()
    logger.info("=" * 80)
    logger.info("INICIANDO STAGE 03: GEOPROCESSAMENTO, SUAVIZAÇÃO BAYESIANA & BLOCAGEM CV")
    logger.info("=" * 80)

    # 1. Stage 03A: Sedes Municipais e Ottobacias Nível 4 da ANA
    logger.info("\n--- [STAGE 03A] SEDES MUNICIPAIS & OTTOBACIAS NÍVEL 4 ---")
    t0 = time.time()
    df_geo = run_ottobacias_stage(env, spec)
    logger.info(f"-> Concluído em {time.time() - t0:.2f}s | Registros: {df_geo.height} | Bacias: {df_geo['ottobacia_id'].n_unique()}")

    # 2. Stage 03B: Suavização Bayesiana Empírica da SMR (k=31 Sedes)
    logger.info("\n--- [STAGE 03B] SUAVIZAÇÃO BAYESIANA EMPÍRICA (SMR k=31 SEDES) ---")
    t1 = time.time()
    df_eb = run_empirical_bayes_stage(env, spec)
    logger.info(f"-> Concluído em {time.time() - t1:.2f}s | Registros: {df_eb.height}")

    # 3. Stage 03C: 5-Fold Nested Spatial Block CV com Dead-Zone de 30 km
    logger.info("\n--- [STAGE 03C] 5-FOLD NESTED SBCV COM DEAD-ZONE DE 30 KM ---")
    t2 = time.time()
    df_cv = run_cross_validation_stage(env, spec)
    logger.info(f"-> Concluído em {time.time() - t2:.2f}s | Registros: {df_cv.height}")

    # 4. Síntese Final
    total_time = time.time() - t_start
    logger.info("\n" + "=" * 80)
    logger.info(f"STAGE 03 CONCLUÍDO COM SUCESSO EM {total_time:.2f}s")
    logger.info("=" * 80)
    logger.info(f"  • Municípios na Malha Integral: {df_geo.height} sedes georreferenciadas (EPSG:5070)")
    logger.info(f"  • Ottobacias Nível 4 Indexadas: {df_geo['ottobacia_id'].n_unique()} bacias hidrográficas")
    logger.info(f"  • Taxas SMR Suavizadas: {df_eb.height} observações (5.570 mun x 3 anos x 5 alvos)")
    logger.info(f"  • Índices de Validação Cruzada: {df_cv.height} registros (685 mun x 5 folds disjuntos)")
    logger.info("  • Todos os artefatos validados por DataContract e registrados em manifest.json")
    logger.info("=" * 80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run_full_stage03()
