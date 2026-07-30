# src/visualize.py
import matplotlib.pyplot as plt

def plot_bar_chart(df, column, top_n=10, title=None, horizontal=True):
    if column not in df.columns:
        raise ValueError(f"Coluna '{column}' não encontrada. Disponíveis: {list(df.columns)}")

    counts = df[column].value_counts(dropna=True).head(top_n)

    fig, ax = plt.subplots(figsize=(10, 6))
    if horizontal:
        counts.sort_values().plot(kind="barh", ax=ax, color="steelblue")
        ax.set_xlabel("Frequência")
    else:
        counts.plot(kind="bar", ax=ax, color="steelblue")
        ax.set_ylabel("Frequência")
        plt.xticks(rotation=45, ha="right")

    ax.set_title(title or f"Top {top_n} - {column}")
    ax.grid(axis="x" if horizontal else "y", alpha=0.3)
    plt.tight_layout()
    plt.show()
    return fig