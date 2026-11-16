import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
BLUE, ORANGE, GREY, RED, GREEN, AMBER = "#1f5fa8", "#d1691c", "#7a7a7a", "#c0392b", "#2e8b57", "#e0a100"
def style():
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .25, "axes.titleweight": "bold", "axes.titlesize": 11,
                         "font.size": 9, "legend.frameon": False, "figure.autolayout": True})
style()
