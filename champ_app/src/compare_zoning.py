"""Compare la segmentation en grille (zoning.py) et par k-means (zoning_kmeans.py)."""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from src.demo_data import generate_synthetic_bands
from src.indices import compute_all_indices
from src.zoning import split_into_zones, annotate_zones
from src.zoning_kmeans import segment_zones_kmeans

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

FIELD_CMAP = LinearSegmentedColormap.from_list(
    "field_health", ["#C4623A", "#D9A441", "#9FBB6C", "#6FA059"]
)

bands = generate_synthetic_bands()
indices_rasters = compute_all_indices(bands)
ndvi = indices_rasters["ndvi"]

# --- grille (approche précédente) ---
grid_zones = annotate_zones(split_into_zones(ndvi, n_rows=8, n_cols=12))
grid_critical = [z for z in grid_zones if z["status"] == "critical"]

# --- k-means (nouvelle approche) ---
label_map, kmeans_zones = segment_zones_kmeans(ndvi, n_zones=6, spatial_weight=0.4)
kmeans_critical = [z for z in kmeans_zones if z["status"] == "critical"]

print("── Grille régulière (8x12 = 96 zones fixes) ──")
print(f"Zones en alerte critique : {len(grid_critical)} / {len(grid_zones)}")
print(f"Exemple de zone : {grid_zones[20]}")

print("\n── K-means (6 zones homogènes) ──")
print(f"Zones en alerte critique : {len(kmeans_critical)} / {len(kmeans_zones)}")
for z in kmeans_zones:
    print(f"  {z['id']}: {z['area_ratio']*100:.1f}% du champ, NDVI moyen={z['mean_value']}, statut={z['status']}")

# --- visualisation comparative ---
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

axes[0].imshow(ndvi, cmap=FIELD_CMAP, vmin=0, vmax=1)
axes[0].set_title("NDVI brut (référence)")
axes[0].axis("off")

zone_colors = ["#C4623A", "#D9A441", "#9FBB6C", "#6FA059", "#4A7A6F", "#7A5FA0"]
cluster_cmap = ListedColormap(zone_colors[:len(kmeans_zones)])
masked_labels = np.ma.masked_where(label_map < 0, label_map)
axes[1].imshow(masked_labels, cmap=cluster_cmap)
axes[1].set_title(f"Zones k-means ({len(kmeans_zones)} zones homogènes)")
axes[1].axis("off")
for z in kmeans_zones:
    axes[1].text(z["centroid_col"], z["centroid_row"], z["id"],
                 color="white", fontsize=11, fontweight="bold", ha="center", va="center")

plt.tight_layout()
out_path = OUTPUT_DIR / "comparaison_grille_vs_kmeans.png"
plt.savefig(out_path, dpi=150, facecolor="#1C1710")
print(f"\nComparaison visuelle exportée : {out_path}")
