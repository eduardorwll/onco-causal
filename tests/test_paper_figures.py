"""Tests for publication figures generation (PDF vector + 300 DPI PNG)."""

from pathlib import Path

from src.visualization.paper_figures import (
    generate_all_figures,
    plot_fig1_spatial_eb_variance_collapse,
    plot_fig2_shap_inflection_curves,
    plot_fig3_detection_bias_forest_plot,
    plot_fig4_counterfactual_and_idv_hotspots,
)


def test_fig1_spatial_eb_variance_collapse(tmp_path: Path) -> None:
    pdf_path, png_path = plot_fig1_spatial_eb_variance_collapse(output_dir=tmp_path)
    assert pdf_path.exists(), f"PDF does not exist: {pdf_path}"
    assert png_path.exists(), f"PNG does not exist: {png_path}"
    assert pdf_path.stat().st_size > 10_000, f"PDF too small: {pdf_path.stat().st_size} bytes"
    assert png_path.stat().st_size > 10_000, f"PNG too small: {png_path.stat().st_size} bytes"


def test_fig2_shap_inflection_curves(tmp_path: Path) -> None:
    pdf_path, png_path = plot_fig2_shap_inflection_curves(output_dir=tmp_path)
    assert pdf_path.exists(), f"PDF does not exist: {pdf_path}"
    assert png_path.exists(), f"PNG does not exist: {png_path}"
    assert pdf_path.stat().st_size > 10_000, f"PDF too small: {pdf_path.stat().st_size} bytes"
    assert png_path.stat().st_size > 10_000, f"PNG too small: {png_path.stat().st_size} bytes"


def test_fig3_detection_bias_forest_plot(tmp_path: Path) -> None:
    pdf_path, png_path = plot_fig3_detection_bias_forest_plot(output_dir=tmp_path)
    assert pdf_path.exists(), f"PDF does not exist: {pdf_path}"
    assert png_path.exists(), f"PNG does not exist: {png_path}"
    assert pdf_path.stat().st_size > 10_000, f"PDF too small: {pdf_path.stat().st_size} bytes"
    assert png_path.stat().st_size > 10_000, f"PNG too small: {png_path.stat().st_size} bytes"


def test_fig4_counterfactual_and_idv_hotspots(tmp_path: Path) -> None:
    pdf_path, png_path = plot_fig4_counterfactual_and_idv_hotspots(output_dir=tmp_path)
    assert pdf_path.exists(), f"PDF does not exist: {pdf_path}"
    assert png_path.exists(), f"PNG does not exist: {png_path}"
    assert pdf_path.stat().st_size > 10_000, f"PDF too small: {pdf_path.stat().st_size} bytes"
    assert png_path.stat().st_size > 10_000, f"PNG too small: {png_path.stat().st_size} bytes"


def test_generate_all_figures(tmp_path: Path) -> None:
    results = generate_all_figures(output_dir=tmp_path)
    assert len(results) == 4, f"Expected 4 figures, got {len(results)}"
    for key, (pdf, png) in results.items():
        assert pdf.exists(), f"Missing PDF for {key}"
        assert png.exists(), f"Missing PNG for {key}"
        assert pdf.stat().st_size > 10_000, f"PDF {key} is unexpectedly small"
        assert png.stat().st_size > 10_000, f"PNG {key} is unexpectedly small"
