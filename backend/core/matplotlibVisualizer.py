import numpy as np
from matplotlib.axes import Axes


def plot_feasible_region(
    ax: Axes,
    c: list[float],
    A: list[list[float]],
    b: list[float],
    inequalities: list[str] | None,
    optimal_point: list[float],
    max_z: float,
) -> None:
    """
    Draws the 2D feasible region for <= and >= constraints with full type safety.
    """
    ax.clear()

    # Explicitly type-hint local variables for static analysis
    x_max: float = 10.0
    y_max: float = 10.0

    x_intercepts: list[float] = [b[i] / A[i][0] for i in range(len(b)) if A[i][0] > 0]
    y_intercepts: list[float] = [b[i] / A[i][1] for i in range(len(b)) if A[i][1] > 0]

    if x_intercepts:
        x_max = max(x_intercepts) * 1.1
    if y_intercepts:
        y_max = max(y_intercepts) * 1.1

    x_max = max(x_max, optimal_point[0] * 1.2)
    y_max = max(y_max, optimal_point[1] * 1.2)

    x_vals: np.ndarray = np.linspace(0, x_max, 400)

    for i in range(len(b)):
        a1: float = A[i][0]
        a2: float = A[i][1]
        rhs: float = b[i]
        ineq: str = inequalities[i] if inequalities and i < len(inequalities) else "<="

        if a2 != 0:
            y_vals: np.ndarray = (rhs - a1 * x_vals) / a2
            ax.plot(x_vals, y_vals, label=f"Constraint {i + 1} ({ineq})")

            if ineq == "<=":
                ax.fill_between(x_vals, 0, y_vals, alpha=0.15)
            else:
                ax.fill_between(x_vals, y_vals, y_max * 2, alpha=0.15)
        elif a1 != 0:
            x_val: float = rhs / a1
            ax.axvline(x=x_val, label=f"Constraint {i + 1} ({ineq})")

            if ineq == "<=":
                ax.axvspan(0, x_val, alpha=0.15)
            else:
                ax.axvspan(x_val, x_max * 2, alpha=0.15)

    ax.plot(
        optimal_point[0],
        optimal_point[1],
        "ro",
        markersize=8,
        label="Optimal Solution",
    )
    ax.annotate(
        f" Z* = {max_z:.2f}\n ({optimal_point[0]:.2f}, {optimal_point[1]:.2f})",
        xy=(optimal_point[0], optimal_point[1]),
        xytext=(10, 5),
        textcoords="offset points",
        fontweight="bold",
    )

    ax.set_xlim(0, x_max)
    ax.set_ylim(0, y_max)
    ax.set_xlabel("$x_1$")
    ax.set_ylabel("$x_2$")
    ax.set_title("2D Simplex Feasible Region")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)