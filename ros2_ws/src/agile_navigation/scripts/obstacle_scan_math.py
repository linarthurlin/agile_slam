"""Pure point-cloud transforms used by the simulated obstacle scan adapter."""
import numpy as np


def transform_finite_points(points, rotation, translation):
    """Drop invalid cloud points before applying a rigid transform."""
    points = np.asarray(points, dtype=float).reshape((-1, 3))
    finite_points = points[np.isfinite(points).all(axis=1)]
    rotation = np.asarray(rotation, dtype=float).reshape((3, 3))
    translation = np.asarray(translation, dtype=float).reshape((3,))
    if not np.isfinite(rotation).all() or not np.isfinite(translation).all():
        return np.empty((0, 3), dtype=float)
    transformed = finite_points @ rotation.T + translation
    return transformed[np.isfinite(transformed).all(axis=1)]
