# src/causal/dag.py
"""Grafo Acíclico Direcionado (DAG) Epidemiológico e Identificação Causal Formal."""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx
import pandas as pd
import polars as pl
from dowhy import CausalModel

from src.core.settings import DomainSpec

logger = logging.getLogger("onco_causal.dag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def build_epidemiological_dag() -> nx.DiGraph:
    """Constrói o Grafo Acíclico Direcionado (DAG) epidemiológico do projeto onco-causal.

    Estrutura Causal:
    - Exposições D1 (agroquímica) e D4 (ocupacional/LINACH).
    - Covariáveis Z_land (uso do solo: floresta, urbanização) confundem D e o desfecho latente Y*.
    - Covariáveis Z_sanit (saneamento: água, esgoto) afetam a vulnerabilidade biológica e Y*.
    - Covariáveis Z_diag (assistencial: CACON/UNACON, leitos, tomógrafos, mamógrafos)
      afetam Y_obs (taxa notificada/observada) via Viés de Detecção.
    - Desfecho latente Y* gera Y_obs.
    """
    g = nx.DiGraph()

    nodes = [
        "D_agro",
        "D_linach",
        "Z_land",
        "Z_sanit",
        "Z_diag",
        "Y_latent",
        "Y_obs",
    ]
    g.add_nodes_from(nodes)

    # Arestas causais substantivas
    edges = [
        # Efeito causal das exposições sobre a etiologia latente
        ("D_agro", "Y_latent"),
        ("D_linach", "Y_latent"),
        # Confundimento ambiental por ocupação/uso do solo
        ("Z_land", "D_agro"),
        ("Z_land", "D_linach"),
        ("Z_land", "Y_latent"),
        # Co-fatores de vulnerabilidade ambiental e sanitária
        ("Z_sanit", "Y_latent"),
        # Mecanismo do Viés de Detecção (Canal de Notificação)
        ("Z_diag", "Y_obs"),
        # Transição da etiologia latente para a taxa observada/suavizada
        ("Y_latent", "Y_obs"),
    ]
    g.add_edges_from(edges)

    return g


def get_dot_graph_for_dowhy(treatment: str, outcome: str) -> str:
    """Gera representação DOT formal para o DoWhy CausalModel com variáveis reais."""
    spec = DomainSpec.from_yaml()
    assist_vars = spec.causal.confounders.assistencial
    sanit_vars = spec.causal.confounders.sanitario
    land_vars = spec.causal.confounders.baseline_land_use

    # A co-exposição alternativa atua como covariável para garantir ortogonalidade mútua
    co_treatment = (
        spec.causal.exposures.linach
        if treatment == spec.causal.exposures.agro
        else spec.causal.exposures.agro
    )

    lines = ["digraph {"]
    # Efeito principal
    lines.append(f'    "{treatment}" -> "{outcome}";')
    lines.append(f'    "{co_treatment}" -> "{outcome}";')

    # Confundidores de solo afetam tratamento e desfecho
    for z in land_vars:
        lines.append(f'    "{z}" -> "{treatment}";')
        lines.append(f'    "{z}" -> "{co_treatment}";')
        lines.append(f'    "{z}" -> "{outcome}";')

    # Confundidores sanitários afetam desfecho
    for z in sanit_vars:
        lines.append(f'    "{z}" -> "{outcome}";')

    # Variáveis de detecção afetam o desfecho observado
    for z in assist_vars:
        lines.append(f'    "{z}" -> "{outcome}";')

    lines.append("}")
    return "\n".join(lines)


def validate_causal_identification(
    df: pd.DataFrame | pl.DataFrame,
    treatment: str,
    outcome: str,
) -> dict[str, Any]:
    """Valida a identificação causal formal via DoWhy usando o critério backdoor."""
    if isinstance(df, pl.DataFrame):
        pdf = df.to_pandas()
    else:
        pdf = df

    dot_graph = get_dot_graph_for_dowhy(treatment=treatment, outcome=outcome)

    model = CausalModel(
        data=pdf,
        treatment=treatment,
        outcome=outcome,
        graph=dot_graph,
    )

    identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)

    backdoor_vars = identified_estimand.get_backdoor_variables()
    logger.info(
        "Identificação concluída para tratamento='%s', desfecho='%s'. Backdoor vars: %s",
        treatment,
        outcome,
        backdoor_vars,
    )

    return {
        "treatment": treatment,
        "outcome": outcome,
        "identified_estimand": identified_estimand,
        "backdoor_variables": backdoor_vars,
        "dot_graph": dot_graph,
    }


def main() -> None:
    """Executa a verificação e validação do DAG causal com dados analíticos reais."""
    logger.info("Construindo e validando o Grafo Acíclico Direcionado (DAG) epidemiológico...")
    dag = build_epidemiological_dag()
    is_dag = nx.is_directed_acyclic_graph(dag)
    logger.info("DAG é acíclico? %s (Nós: %d, Arestas: %d)", is_dag, len(dag.nodes), len(dag.edges))
    if not is_dag:
        raise ValueError("O grafo epidemiológico contém ciclos direcionados inválidos!")

    spec = DomainSpec.from_yaml()
    from src.core.settings import EnvSettings
    env = EnvSettings()
    panel_path = env.features_dir / "master_analytical_panel.parquet"
    if not panel_path.exists():
        logger.warning("Painel analítico não encontrado em %s para teste com dados reais.", panel_path)
        return

    df = pl.read_parquet(panel_path).filter(pl.col("target_cancer") == "hematologico_infantojuvenil")
    treatment = spec.causal.exposures.agro
    outcome = "smr_suavizada_eb"

    result = validate_causal_identification(df, treatment, outcome)
    print("\n--- DAG Epidemiológico Validado com Sucesso ---")
    print(f"Tratamento: {result['treatment']}")
    print(f"Desfecho: {result['outcome']}")
    print(f"Variáveis Backdoor identificadas: {result['backdoor_variables']}")
    print("-------------------------------------------------\n")


if __name__ == "__main__":
    main()
