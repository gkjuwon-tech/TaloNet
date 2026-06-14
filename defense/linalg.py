"""Minimal pure-Python linear algebra helpers.

Kept dependency-free on purpose: the defensive modules in this package must be
auditable and runnable on an embedded flight computer without pulling in a
large BLAS stack. Matrices are plain ``list[list[float]]`` (row-major) and
vectors are ``list[float]``.

Only the small, well-conditioned systems needed for weighted least-squares
GNSS positioning (typically 4 unknowns: x, y, z, receiver-clock-bias) are
required, so a straightforward Gauss-Jordan solve is sufficient and easy to
verify by inspection.
"""

from __future__ import annotations

Matrix = list[list[float]]
Vector = list[float]


def transpose(a: Matrix) -> Matrix:
    return [list(col) for col in zip(*a)]


def matmul(a: Matrix, b: Matrix) -> Matrix:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a: Matrix, v: Vector) -> Vector:
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def identity(n: int) -> Matrix:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def invert(a: Matrix) -> Matrix:
    """Invert a square matrix via Gauss-Jordan elimination with partial pivoting."""
    n = len(a)
    aug = [list(a[i]) + identity(n)[i] for i in range(n)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot_row][col]) < 1e-12:
            raise ValueError("matrix is singular or ill-conditioned")
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        aug[col] = [v / pivot for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor != 0.0:
                aug[r] = [v - factor * w for v, w in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def weighted_least_squares(h: Matrix, y: Vector, weights: Vector | None = None):
    """Solve the (optionally weighted) least-squares problem ``H x ~= y``.

    Returns ``(x_hat, residuals, gain)`` where ``gain = (H^T W H)^-1 H^T W`` is
    the pseudo-inverse used to map measurements to the state estimate. This is
    the standard GNSS snapshot least-squares estimator (see any GNSS textbook,
    e.g. Kaplan & Hegarty, "Understanding GPS/GNSS").
    """
    m = len(h)
    if weights is None:
        weights = [1.0] * m
    ht = transpose(h)
    htw = [[ht[i][k] * weights[k] for k in range(m)] for i in range(len(ht))]
    htwh = matmul(htw, h)
    gain = matmul(invert(htwh), htw)
    x_hat = matvec(gain, y)
    residuals = [y[k] - sum(h[k][j] * x_hat[j] for j in range(len(x_hat))) for k in range(m)]
    return x_hat, residuals, gain
